import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceInstructEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from htmlTemplates import bot_template, css, user_template
from langchain.llms import HuggingFaceHub 

def get_pdf_text(pdf_docs):
    """
    This function takes a list of PDF documents as input and returns a string
    containing the text of all the PDF documents.
    Args:
        pdf_docs: A list of PDF documents.
    Returns:
        A string containing the text of all the PDF documents.
    """
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def get_text_chunks(text):
    """
    This function takes a string of text as input and returns a list of
    text chunks. Each chunk is a substring of the original text that is
    no longer than the specified chunk size.
    Args:
        text: A string of text.
    Returns:
        A list of text chunks.
    """    
    # Create a text splitter
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000, # Maximum number of characters in a chunk
        chunk_overlap=200, # Number of characters that are allowed to overlap between adjacent chunks
        length_function=len # Used to calculate the length of a chunk
    )
    # Split the text into chunks
    chunks = text_splitter.split_text(text)
    return chunks


def get_vector_store(text_chunks):
    """
    This function takes a list of text chunks as input and returns a
    vector store. 
    Args:
        text_chunks: A list of text chunks.
    Returns:
        A FAISS vector store.
    """
    # Load the OpenAI embeddings
    #embeddings = OpenAIEmbeddings() # Not free
    embeddings = HuggingFaceInstructEmbeddings(model_name="BAAI/bge-base-en") # Free
    # Create a FAISS index
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore


def get_conversation_chain(vectorstore):
    """
    This function takes a vector store as input and returns a
    conversation chain. The conversation chain is a sequence of
    text chunks that can be used to generate a conversation.
    Args:
        vectorstore: A FAISS vector store.
    Returns:
        A ConversationChain object.
    """
    # Create a language model
    llm = ChatOpenAI()
    #llm = HuggingFaceHub(repo_id="google/flan-t5-xxl", model_kwargs={"temperature":0.5, "max_length":512})
    # Create a conversation memory
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    # Create a conversation chain
    convertation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    return convertation_chain


def handle_user_input(user_question):
    """
    This function takes a user question as input and returns a response.
    The response is generated by the conversation chain.
    Args:
        user_question: The user question.
    Returns:
        The response.
    """
    # Get the conversation chain and Generate a response
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)

def main():
    load_dotenv()
    st.set_page_config(page_title='Chat with multiple PDFs', page_icon=':books:')
    st.write(css, unsafe_allow_html=True)

    # Just to take care of streamlit reload the whole conversation, use session state
    if "conversation" not in st.session_state:
        st.session_state.conversation = None

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None    

    st.header('Chat with multiple PDFs :books:')
    user_question = st.text_input('Ask a question about your documents:')
    if user_question:
        handle_user_input(user_question)

    #st.write(user_template.replace("{{MSG}}", "Hello robot"), unsafe_allow_html=True)
    #st.write(bot_template.replace("{{MSG}}", "Hello human"), unsafe_allow_html=True)

    with st.sidebar:
        st.subheader('Your documents')
        pdf_docs = st.file_uploader(
            'Upload you files here and press to process', accept_multiple_files=True)
        if st.button('Process'):
            with st.spinner("Processing"):
                # Get the PDFs Text
                raw_text = get_pdf_text(pdf_docs)

                # Get the text Chunks
                text_chunks = get_text_chunks(raw_text)

                # Create the Vector Store
                vector_store = get_vector_store(text_chunks)

                # Create a conversation chain
                st.session_state.conversation = get_conversation_chain(vector_store)


if __name__ == '__main__':
    main()