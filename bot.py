from telegram.ext import Updater, CommandHandler
from queue import Queue
from model import *
import requests
import json
import time, threading
import gitlab
import os
import persistence
import traceback

# Tor socks5 proxy, cause I am in Russia, duh
REQUEST_KWARGS={
    'proxy_url': 'socks5://localhost:9150'
}
# Don't put your gitlab tokens to git
with open('gitlab_token', 'r') as token_file: 
    GITLAB_TOKEN = token_file.read()
GITLAB_ADDRESS = 'http://gitlab.dibr.lanit'

# Don't put your telegram token to git
with open('telegram_token', 'r') as token_file: 
    TELEGRAM_TOKEN = token_file.read()

PROJECT_STATE_FILENAME = 'projects_state.json'
CHAT_IDS_FILENAME = 'chat_ids.json'

DEBUG_PROJECT = 'OSP/pipeline-sandbox'

messages = Queue(1000)

# last state of all projects
projects_state = {}
projects_state = persistence.load(PROJECT_STATE_FILENAME)

# ids of chats to notify people
chat_ids = []
chat_ids = persistence.load(CHAT_IDS_FILENAME)

def get_project_state(gl, gl_project):
    project_name = gl_project.path_with_namespace
    pipeline_states = {}
    project_state = ProjectState(project_name, pipeline_states)
    gl_pipelines = gl_project.pipelines.list()

    for gl_pipeline in gl_pipelines:
        ref = gl_pipeline.ref
        # ignoring pipelines without ref and pipelines with pending statuses
        if (ref != None and gl_pipeline.status in ['canceled', 'success', 'failed']):
            existing_pipeline_states = pipeline_states.get(ref)
            # saving only last pipeline for any given ref
            if (existing_pipeline_states == None or existing_pipeline_states.id < gl_pipeline.id):
                pipeline_states[ref] = PipelineState(gl_pipeline.id, gl_pipeline.ref, gl_pipeline.status, gl_pipeline.web_url)
    if project_name == DEBUG_PROJECT:
        print("DEBUG PROJECT PIPELINES: {}".format(gl_pipelines))
        print("DEBUG PROJECT PIPELINE STATES: {}".format(pipeline_states))
    return project_state


# building state for all projects and all pipelines we can put our hands on
def get_projects_state(gl):
    acc = {}
    gl_projects = gl.projects.list()
    for gl_project in gl_projects:
        try:
            project_state = get_project_state(gl, gl_project)
            acc[project_state.project_name] = project_state
        except Exception as e:
            print("ERROR: failed to get project state: {}".format(e))
            traceback.print_exc()
    return acc


def find_interesting_events(o_projects_state, n_projects_state):
    events = []
    try:
        for project_name, n_project_state in n_projects_state.items():
            o_project_state = o_projects_state.get(project_name)
            if (o_project_state != None):
                if n_project_state.project_name == DEBUG_PROJECT:
                    print("DEBUB PROJECT OLD STATE: {}".format(o_project_state))
                    print("DEBUB PROJECT NEW STATE: {}".format(n_project_state))

                for ref, n_pipeline_state in n_project_state.pipeline_states.items():
                    o_pipeline_state = o_project_state.pipeline_states.get(ref)
                    if (o_pipeline_state != None):
                        old_pipeline_failed = o_pipeline_state.status == 'failed' or o_pipeline_state.status == 'canceled'
                        new_pipeline_failed = n_pipeline_state.status == 'failed' or n_pipeline_state.status == 'canceled'
                        new_pipeline = o_pipeline_state.id != n_pipeline_state.id 
                        if (not old_pipeline_failed or new_pipeline) and new_pipeline_failed:
                            events.append(PipelineEvent(PipelineEventType.FAILED, project_name, ref, n_pipeline_state.url))
                        elif old_pipeline_failed and not new_pipeline_failed:
                            events.append(PipelineEvent(PipelineEventType.RESTORED, project_name, ref, n_pipeline_state.url))

    except Exception as e:
        print("ERROR: failed to find interesting events {}".format(e))
        traceback.print_exc()
    return events


def send_events(events):
    try:
        for event in events:
            if event.event_type == PipelineEventType.FAILED:
                push_message_to_every_chat("\U000026A0  Pipeline for {} : {} failed. {}".format(event.project_name, event.ref, event.url))   
                
            elif event.event_type == PipelineEventType.RESTORED:
                push_message_to_every_chat("\U00002705  Pipeline for {} : {} restored. {}".format(event.project_name, event.ref, event.url))  
    except Exception as e:
        print("ERROR: failed to find interesting events {}".format(e))    
        traceback.print_exc()   

def check_projects():
    global projects_state
    gl = None
    try:
        gl = gitlab.Gitlab(GITLAB_ADDRESS, private_token=GITLAB_TOKEN) 
    except Exception as e:
        print("ERROR: failed to connect to gitlab: {}".format(e))
        traceback.print_exc()
    if (gl != None):
        new_projects_state = get_projects_state(gl)
        events = find_interesting_events(projects_state, new_projects_state)
        if (len(events) > 0):
            print("EVENTS: {}".format(events))
            send_events(events)
        persistence.save(new_projects_state, PROJECT_STATE_FILENAME)
        projects_state = new_projects_state



def register_chat(chat_id):
    global chat_ids
    if chat_id not in chat_ids:
        chat_ids.append(chat_id)
        persistence.save(chat_ids, CHAT_IDS_FILENAME)
        push_message_to_chat(chat_id, "starting to spam you")
    else:
        push_message_to_chat(chat_id, "already spamming you")

def unregister_chat(chat_id):
    global chat_ids
    if chat_id in chat_ids:
        chat_id.remove(chat_id)
        persistence.save(chat_ids, CHAT_IDS_FILENAME)
        push_message_to_chat(chat_id, "stopped spamming you")
    else:
        push_message_to_chat(chat_id, "not spamming you")

def push_message_to_every_chat(text):
    global chat_ids
    #print("pushing {} to chats {}".format(text, chat_ids))
    for chat_id in chat_ids:
        push_message_to_chat(chat_id, text)

def push_message_to_chat(chat_id, text):
    global messages
    #print("pushing {} to chat {}".format(text, chat_id))
    messages.put(Message(chat_id, text))


def trottled_sending(bot, job):
    global messages
    if not messages.empty():
        message = messages.get()
        if not message is None:
            bot.send_message(chat_id = message.chat_id, text = message.text)

def start(bot, update):
    chat_id = update.message.chat.id
    register_chat(chat_id)

def stop(bot, update):
    chat_id = update.message.chat.id
    register_chat(chat_id)
    push_message_to_chat(chat_id, "ping")

def ping(bot, update):
    push_message_to_every_chat("ping")

# periodic job that checks pipelines
def check_pipelines_job():
    try:
        print("Checking piplines: {}".format(time.ctime()))
        check_projects()
    except Exception as e:
        print("ERROR: {}".format(e))
        traceback.print_exc()
    finally:    
        threading.Timer(20, check_pipelines_job).start()

def main():
    # run job
    check_pipelines_job()
    try:
        # connect to telegram
        updater = Updater(TELEGRAM_TOKEN, request_kwargs=REQUEST_KWARGS)
        updater.dispatcher.add_handler(CommandHandler('ping', ping))
        updater.dispatcher.add_handler(CommandHandler('start', start))
        updater.dispatcher.add_handler(CommandHandler('stop', stop))
        updater.job_queue.run_repeating(trottled_sending, interval=5, first=0)
        updater.start_polling()
        print('Telegram bot polling')
        updater.idle()
        print('Telegram bot idle')
    except Exception as e:
        print("ERROR: Telegram error {}".format(e))
        traceback.print_exc()

main()
