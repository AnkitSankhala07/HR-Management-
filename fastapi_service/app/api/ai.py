from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Connection

from ..ai import copilot, llm
from ..dependencies import CurrentUser, current_user, get_conn
from ..schemas.ai import ChatRequest, ChatResponse
from ..services import conversations as conv

router = APIRouter(prefix="/ai", tags=["AI HR Copilot"])


@router.post("/chat", response_model=ChatResponse, summary="Ask the HR Copilot (RBAC-enforced)")
def chat(body: ChatRequest, user: CurrentUser = Depends(current_user), conn: Connection = Depends(get_conn)):
    cid = body.conversation_id
    if cid is not None and not conv.owned(conn, user.id, cid):
        raise HTTPException(404, "Conversation not found")
    if cid is None:
        cid = conv.create(conn, user.id, body.message)
    conv.add(conn, cid, "user", body.message)
    try:
        a = copilot.answer(conn, user, body.message)
    except HTTPException as e:
        if e.status_code == 403:   # keep the denial in the history, then surface the 403 to the client
            conv.add(conn, cid, "assistant", f"Unauthorized: {e.detail}")
        raise
    text = llm.polish(body.message, a.text) if not a.refused else a.text
    conv.add(conn, cid, "assistant", text)
    return ChatResponse(conversation_id=cid, answer=text, refused=a.refused, tool=a.tool)


@router.post("/hr-assistant", response_model=ChatResponse, summary="Alias of /ai/chat")
def hr_assistant_post(body: ChatRequest, user: CurrentUser = Depends(current_user), conn: Connection = Depends(get_conn)):
    return chat(body, user, conn)


@router.get("/hr-assistant", summary="Suggested questions for the signed-in role")
def hr_assistant(user: CurrentUser = Depends(current_user)):
    return {"role": user.role, "suggestions": copilot.SUGGESTIONS.get(user.role, copilot.SUGGESTIONS["EMPLOYEE"])}


@router.get("/conversations", summary="List my conversations")
def conversations(user: CurrentUser = Depends(current_user), conn: Connection = Depends(get_conn)):
    return conv.list_(conn, user.id)


@router.get("/conversations/{cid}", summary="Get one conversation with messages")
def conversation(cid: int, user: CurrentUser = Depends(current_user), conn: Connection = Depends(get_conn)):
    if not conv.owned(conn, user.id, cid):
        raise HTTPException(404, "Conversation not found")
    return {"id": cid, "messages": conv.messages(conn, cid)}


@router.delete("/conversations/{cid}", summary="Delete a conversation")
def delete_conversation(cid: int, user: CurrentUser = Depends(current_user), conn: Connection = Depends(get_conn)):
    if not conv.owned(conn, user.id, cid):
        raise HTTPException(404, "Conversation not found")
    conv.delete(conn, cid)
    return {"deleted": True}
