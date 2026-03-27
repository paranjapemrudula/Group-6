import os
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate

# Finance-specific system prompt
FINANCE_PROMPT = PromptTemplate(
    input_variables=["history", "input"],
    template="""
    You are MyFinance AI Assistant. You help users with:
    - Budget planning and expense tracking
    - Investment advice and portfolio analysis
    - Loan and EMI calculations
    - Tax planning and savings tips
    - Financial goal setting

    Conversation History:
    {history}

    User: {input}
    MyFinance Assistant:"""
)

def get_chatbot():
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    memory = ConversationBufferMemory()
    chain = ConversationChain(
        llm=llm,
        memory=memory,
        prompt=FINANCE_PROMPT,
        verbose=True
    )
    return chain