import time
import streamlit as st
from databricks.sdk import WorkspaceClient

SPACE_ID = "01f150aaaa9e12ffb3977a7b0996556d"

st.set_page_config(page_title="Mercado Segurador", page_icon="🛡️", layout="wide")
st.title("🛡️ Mercado Segurador — Genie AI")
st.caption("Faça perguntas sobre os dados do mercado segurador em linguagem natural.")

w = WorkspaceClient(
    host=st.secrets["DATABRICKS_HOST"],
    token=st.secrets["DATABRICKS_TOKEN"],
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


def wait_for_message(conversation_id, message_id, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        msg = w.genie.get_message(
            space_id=SPACE_ID,
            conversation_id=conversation_id,
            message_id=message_id,
        )
        if msg.status and msg.status.value in ("COMPLETED", "FAILED", "CANCELLED"):
            return msg
        time.sleep(2)
    raise TimeoutError("Genie demorou demais para responder.")


def extract_response(msg):
    parts = []
    if msg.attachments:
        for att in msg.attachments:
            if hasattr(att, "text") and att.text:
                parts.append(att.text.content)
            if hasattr(att, "query") and att.query:
                if att.query.description:
                    parts.append(att.query.description)
                if att.query.query:
                    parts.append(f"```sql\n{att.query.query}\n```")
    return "\n\n".join(parts) if parts else "Genie não retornou resposta. Tente reformular."


if prompt := st.chat_input("Ex: Quais seguradoras têm maior volume de prêmios?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando Genie..."):
            try:
                if st.session_state.conversation_id is None:
                    resp = w.genie.start_conversation(space_id=SPACE_ID, content=prompt)
                    st.session_state.conversation_id = resp.conversation_id
                    message_id = resp.message_id
                else:
                    resp = w.genie.create_message(
                        space_id=SPACE_ID,
                        conversation_id=st.session_state.conversation_id,
                        content=prompt,
                    )
                    message_id = resp.message_id

                msg = wait_for_message(st.session_state.conversation_id, message_id)
                answer = extract_response(msg)
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

            except Exception as e:
                st.error(f"Erro ao consultar Genie: {e}")

if st.session_state.messages:
    if st.button("🔄 Nova conversa"):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.rerun()
