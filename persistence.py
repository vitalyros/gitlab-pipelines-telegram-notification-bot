from model import *
from json import JSONEncoder
import os
import traceback
import json

TMP_FILENAME_PREFIX = ".tmp"

class DictEncoder(JSONEncoder):
    def default(self, o):
        result = o.__dict__   
        result['__type__'] = type(o).__name__ 
        return result

def decoder(obj):
    type_name = obj.get('__type__')
    if (type_name == 'ProjectState'):
        pipeline_states = obj.get('pipeline_states')
        if pipeline_states is None:
            pipeline_states = {}
        return ProjectState(obj['project_name'], pipeline_states)
    elif (type_name == 'PipelineState'):
        return PipelineState(obj['id'], obj['ref'], obj['status'], obj['url'])
    else:
        return obj 

def save(obj, filename):
    tmp_filename = filename + TMP_FILENAME_PREFIX
    tmp_file_save_success = False
    try:
        os.remove(tmp_filename)
    except Exception as e:
        pass
    try:    
        with open(tmp_filename, 'w') as out_file:
            json.dump(obj, out_file, cls=DictEncoder)
        tmp_file_save_success = True
    except Exception as e:
        print("ERROR: failed to save to file {}: {}".format(tmp_filename, e))
        traceback.print_exc()
    if tmp_file_save_success:
        try:
            os.remove(filename)
        except Exception as e:
            pass      
        try:
            os.rename(tmp_filename, filename)
        except Exception as e:
            print("ERROR: failed rename tmp file {} to {}: {}".format(tmp_filename, filename, e))    
            traceback.print_exc() 

def do_load(filename):
    with open(filename, 'r') as in_file:
        file_data = in_file.read()
        #print(file_data)
        result = json.loads(file_data, object_hook = decoder)
        #print("Successfully loaded {}: {}".format(filename, result))
        return result

def load(filename):
    try:
        return do_load(filename)
    except Exception as e1:
        print("ERROR: failed to load file {}: {}".format(filename, e1))
        traceback.print_exc()
        try:
            tmp_filename = filename + TMP_FILENAME_PREFIX
            return do_load(tmp_filename)
        except Exception as e2:
            print("ERROR: failed to load file {}: {}".format(tmp_filename, e2))    
            traceback.print_exc()

    
    