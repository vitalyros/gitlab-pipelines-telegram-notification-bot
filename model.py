from enum import Enum 

class DataClass:
    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        return str(self.__dict__)

class Message(DataClass):
    def __init__(self, chat_id: str, text: str):
        self.chat_id = chat_id
        self.text = text

class ProjectState(DataClass):
    def __init__(self, project_name: str, pipeline_states):
        self.project_name = project_name
        self.pipeline_states = pipeline_states

class PipelineState(DataClass):
    def __init__(self, id: int, ref: str, status: str, url: str):
        self.id = id
        self.ref = ref
        self.status = status
        self.url = url

class PipelineEventType(Enum):
    FAILED = 1
    RESTORED = 2
        
class PipelineEvent(DataClass):
    def __init__(self, event_type: PipelineEventType, project_name: str, ref: str, url: str, pipeline_id: int):
        self.event_type = event_type
        self.project_name = project_name
        self.ref = ref
        self.url = url
        self.pipeline_id = pipeline_id
