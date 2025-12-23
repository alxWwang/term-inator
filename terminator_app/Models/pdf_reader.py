from io import BytesIO
import PyPDF2
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter
import requests
import feedparser
    
def parse_arxiv_feed_xml(xml_string, download_pdfs=False):
    feed = feedparser.parse(xml_string)
    results = []
    for entry in feed.entries:
        pdf_link = next(
            (l.href for l in entry.links
             if l.get('type') == 'application/pdf' or l.get('title') == 'pdf'),
            None
        )
        item = {
            "id": entry.get("id"),
            "title": entry.get("title"),
            "summary": entry.get("summary"),
            "updated": entry.get("updated"),
            "published": entry.get("published"),
            "authors": [a.get("name") for a in entry.get("authors", [])],
            "categories": [c.get("term") for c in entry.get("tags", [])],
            "pdf_link": pdf_link,
        }

        if download_pdfs and pdf_link:
            r = requests.get(pdf_link, timeout=10)
            r.raise_for_status()
            pdf_file = BytesIO(r.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = "".join((p.extract_text() or "") for p in pdf_reader.pages)
            item["pdf_text"] = text

        results.append(item)
    return results

def process_text_and_get_vectorstore(text: str) -> FAISS:
    """Splits text, creates embeddings, and builds the FAISS vector store."""
    print("Building Vector Store (FAISS)...")
    
    text_splitter = CharacterTextSplitter(
        separator="\n", 
        chunk_size=512,
        chunk_overlap=128,
        length_function=len
    )
    chunks = text_splitter.split_text(text)

    # Use a high-quality, local-first embedding model
    # This relies on your previous successful installation of sentence-transformers
    embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-mpnet-base-v2')
    
    knowledgeBase = FAISS.from_texts(chunks, embeddings)
    print(f"Vector Store built with {len(chunks)} chunks.")
    return knowledgeBase