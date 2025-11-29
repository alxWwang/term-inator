from typing import TypedDict, List, Optional, Union

class MessagePartDict(TypedDict, total=False):
    text: str

class MessageDict(TypedDict, total=False):
    role: str
    parts: List[MessagePartDict]
    timestamp: Optional[str]

class UserModelPairDict(TypedDict, total=False):
    user: MessageDict
    model: MessageDict
    ai_pending: bool
    gen_id: str

class ConversationDict(TypedDict, total=False):
    id: Optional[str]
    timestamp: Optional[str]
    title: Optional[str]
    messages: List[Union[MessageDict, UserModelPairDict]]
