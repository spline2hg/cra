import os
from typing import List, Optional

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
from langchain_cohere import CohereEmbeddings
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_community.vectorstores import Chroma
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from cra.config import settings


class CodebaseChat:

    def __init__(self, codebase_path: Optional[str] = None):
        """
        Initialize chat system.

        Args:
            codebase_path: Path to codebase to index
        """
        self.codebase_path = os.path.abspath(codebase_path or settings.codebase_path)

        # Create path-specific cache directory using just the final directory/file name
        path_name = os.path.basename(self.codebase_path.rstrip(os.sep))
        self.persist_dir = os.path.join(settings.cache_dir, f"index_{path_name}")

        self.embed_model = settings.embed_model
        self.gemini_model = settings.gemini_model
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        self.latest_report_path = settings.latest_report_path
        self.vectorstore = None
        self.retriever = None
        self.retrieval_chain = None
        self.documents = None

        # Add conversation history
        self.chat_history = ChatMessageHistory()
        self.conversational_chain = None

    def load_documents(self) -> List:
        parser_loader = GenericLoader.from_filesystem(
            self.codebase_path,
            glob="**/*",
            suffixes=[".py", ".js"],
            parser=LanguageParser(),
        )
        code_docs = parser_loader.load()

        if os.path.isfile(self.codebase_path):
            loader = TextLoader(self.codebase_path, encoding="utf-8")
            other_docs = [loader.load()[0]] if loader.load() else []
        else:
            other_loader = DirectoryLoader(
                self.codebase_path,
                glob=[
                    "**/*.txt",
                    "**/*.md",
                    "**/*.json",
                    "**/*.yaml",
                    "**/*.yml",
                    "**/*.toml",
                    "**/*.ini",
                    "**/*.cfg",
                    "**/*.conf",
                    "**/*.xml",
                    "**/*.html",
                    "**/*.css",
                    "**/*.csv",
                ],
                loader_cls=TextLoader,
                loader_kwargs={"encoding": "utf-8"},
                show_progress=False,
                silent_errors=True,
            )
            other_docs = other_loader.load()

        all_docs = code_docs + other_docs
        print(
            f"Loaded {len(code_docs)} code docs, {len(other_docs)} other docs, {len(all_docs)} total"
        )
        return all_docs

    def split_documents(self, docs: List) -> List:
        chunks = []
        fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        js_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.JS,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        py_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        for doc in docs:
            lang = doc.metadata.get("language")
            source = doc.metadata.get("source", "")
            content_len = len(doc.page_content or "")

            if lang and (
                "js" in str(lang).lower() or "javascript" in str(lang).lower()
            ):
                chunks.extend(js_splitter.split_documents([doc]))
            elif lang and ("python" in str(lang).lower() or source.endswith(".py")):
                chunks.extend(py_splitter.split_documents([doc]))
            else:
                if content_len > 1500:
                    chunks.extend(fallback_splitter.split_documents([doc]))
                else:
                    chunks.append(doc)

        print(f"Split into {len(chunks)} chunks")
        return chunks

    def create_vectorstore(self, chunks: List):
        try:
            # Try Cohere embeddings first if API key is available
            if os.getenv("COHERE_API_KEY"):
                try:
                    embeddings = CohereEmbeddings(model="embed-english-v3.0")
                    print("Using Cohere embeddings")
                except Exception as e:
                    print(f"Failed to initialize Cohere embeddings: {e}")
                    # Fall back to Google embeddings
                    embeddings = GoogleGenerativeAIEmbeddings(model=self.embed_model)
                    print("Using Google embeddings")
            elif os.getenv("GOOGLE_API_KEY"):
                try:
                    embeddings = GoogleGenerativeAIEmbeddings(model=self.embed_model)
                    print("Using Google embeddings")
                except Exception as e:
                    print(f"Failed to initialize Google embeddings: {e}")
                    print("Embedding functionality will be disabled.")
                    self.vectorstore = Chroma(persist_directory=self.persist_dir)
                    self.vectorstore.add_documents(chunks)
                    return

            self.vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=self.persist_dir,
            )
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"API quota exceeded. Please wait and try again later.")
                print(f"Error: {e}")
                raise RuntimeError("API quota exceeded. Please try again later.") from e
            else:
                raise

    def setup_retriever(self):
        if self.vectorstore is None:
            raise ValueError(
                "Vectorstore not initialized. Call create_vectorstore first."
            )

        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity", search_kwargs={"k": 4}
        )

    def setup_chain(self):
        if self.retriever is None:
            raise ValueError("Retriever not initialized. Call setup_retriever first.")

        llm = ChatGoogleGenerativeAI(model=self.gemini_model)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert coding assistant for the CRA (Code Review Assistant) project. Use the provided code snippets and file metadata to answer questions about the codebase.

        Each code snippet is prefixed with its file path in square brackets (e.g., [src/cra/chat.py]).

        When helping users with coding questions:
        1. Analyze the code context carefully to understand the structure and functionality
        2. Provide specific, actionable advice based on the actual code
        3. When suggesting improvements, explain the reasoning behind your recommendations
        4. If you see issues like security vulnerabilities, complexity problems, or maintainability concerns, point them out
        5. Focus on the code quality, best practices, and potential improvements

        For example:
        - If asked about a function, explain its purpose and how it works
        - If asked about classes, describe their responsibilities and relationships
        - If asked for improvements, suggest specific refactoring opportunities
        - If asked about dependencies, explain how components interact

        Context: {context}""",
                ),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
            ]
        )
        doc_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)
        self.retrieval_chain = create_retrieval_chain(
            retriever=self.retriever, combine_docs_chain=doc_chain
        )

        # Wrap the chain with message history for conversational context
        self.conversational_chain = RunnableWithMessageHistory(
            self.retrieval_chain,
            lambda session_id: self.chat_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

    def initialize(self):
        if self.documents is None:
            print("Loading documents...")
            self.documents = self.load_documents()

        print("Splitting documents...")
        chunks = self.split_documents(self.documents)

        print("Creating vector store...")
        self.create_vectorstore(chunks)

        print("Setting up retriever...")
        self.setup_retriever()

        print("Setting up chain...")
        self.setup_chain()

        print("Chat system ready!")

    def get_latest_report_content(self):
        """Get latest report content."""
        try:
            if os.path.exists(self.latest_report_path):
                with open(self.latest_report_path, "r", encoding="utf-8") as f:
                    return f.read()
            return None
        except Exception as e:
            print(f"Could not read latest report: {e}")
            return None

    def analyze_latest_report(self):
        """Analyze latest report with LLM."""
        content = self.get_latest_report_content()
        if not content:
            return "No latest report found."

        try:
            from cra.llm_report import generate_llm_summary

            return generate_llm_summary(content)
        except Exception as e:
            return f"Error analyzing report: {str(e)}"

    def add_documents_to_index(self, new_docs):
        """Add new documents to existing index."""
        if self.vectorstore is None:
            raise ValueError("Vectorstore not initialized.")

        print("Splitting new documents...")
        chunks = self.split_documents(new_docs)

        print(f"Adding {len(chunks)} chunks to index...")
        self.vectorstore.add_documents(chunks)
        print("Documents added successfully!")

    def load_existing_index(self):
        """Load existing vector store if available."""
        try:
            from dotenv import load_dotenv

            load_dotenv()
            if not os.path.exists(self.persist_dir) or not os.listdir(self.persist_dir):
                return False

            print("Loading existing vector store...")
            # Try Cohere embeddings first if API key is available
            if os.getenv("COHERE_API_KEY"):
                try:
                    embeddings = CohereEmbeddings(model="embed-english-v3.0")
                    print("Using Cohere embeddings")
                except Exception as e:
                    print(f"Failed to initialize Cohere embeddings: {e}")
                    # Fall back to Google embeddings
                    embeddings = GoogleGenerativeAIEmbeddings(model=self.embed_model)
                    print("Using Google embeddings")
            elif os.getenv("GOOGLE_API_KEY"):
                try:
                    embeddings = GoogleGenerativeAIEmbeddings(model=self.embed_model)
                    print("Using Google embeddings")
                except Exception as e:
                    print(f"Failed to initialize Google embeddings: {e}")
                    print("Embedding functionality will be disabled.")
                    self.vectorstore = Chroma(persist_directory=self.persist_dir)
                    self.setup_retriever()
                    self.setup_chain()
                    print("Existing index loaded!")
                    return True

            self.vectorstore = Chroma(
                persist_directory=self.persist_dir, embedding_function=embeddings
            )
            self.setup_retriever()
            self.setup_chain()
            print("Existing index loaded!")
            return True
        except Exception as e:
            print(f"Could not load existing index: {e}")
            return False

    def ask(self, query: str) -> str:
        """
        Ask a question about the codebase.

        Args:
            query: Question to ask

        Returns:
            Answer to the question
        """
        if self.retrieval_chain is None:
            raise ValueError("Chat system not initialized.")

        try:
            # Add user message to history
            self.chat_history.add_message(HumanMessage(content=query))

            # Get context for display (same as before)
            docs = self.retriever.get_relevant_documents(query)
            
            # Check if user wants to include the latest report
            if "@report" in query.lower():
                # Get the latest report content
                report_content = self.get_latest_report_content()
                if report_content:
                    from langchain_core.documents import Document
                    report_doc = Document(
                        page_content=report_content,
                        metadata={"source": "Latest Linting Report"}
                    )
                    docs.append(report_doc)

            context_text = "\n\n".join(
                [f"[{d.metadata.get('source')}]\n{d.page_content}" for d in docs]
            )

            print("=== CONTEXT SENT TO LLM ===")
            print(context_text)
            print("=== END CONTEXT ===\n")

            # Use conversational chain with history
            result = self.conversational_chain.invoke(
                {"input": query}, config={"configurable": {"session_id": "unused"}}
            )

            # Add AI response to history and return the answer
            if isinstance(result, dict):
                # Try to get the answer from the result
                answer = (
                    result.get("answer") or result.get("output") or result.get("result")
                )
                if answer:
                    self.chat_history.add_message(AIMessage(content=answer))
                    return answer
                else:
                    # If we can't find a proper answer, convert the whole result to string
                    answer_str = str(result)
                    self.chat_history.add_message(AIMessage(content=answer_str))
                    return answer_str
            else:
                # If result is not a dict, convert to string
                answer_str = str(result)
                self.chat_history.add_message(AIMessage(content=answer_str))
                return answer_str
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            self.chat_history.add_message(AIMessage(content=error_msg))
            return error_msg

    def get_conversation_history(self):
        """Get the current conversation history."""
        return self.chat_history.messages

    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.chat_history.clear()


def quick_ask(query: str, codebase_path: Optional[str] = None) -> str:
    """
    Quick question about codebase.

    Args:
        query: Question to ask
        codebase_path: Path to codebase

    Returns:
        Answer to question
    """
    chat = CodebaseChat(codebase_path=codebase_path)
    if not chat.load_existing_index():
        chat.initialize()
    return chat.ask(query)
