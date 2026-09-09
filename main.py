from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
import httpx
import os
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError
from database import Post, Variant, get_db
from schemas import PostCreate, VariantCreate, VariantGenerate
from bs4 import BeautifulSoup


app = FastAPI()

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def clean_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")

    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    return soup.get_text(separator=" ", strip=True)

@app.post("/posts", status_code=201)
def create_post(post: PostCreate, db: Session = Depends(get_db)):

    if not post.source_url and not post.raw_content:
        raise HTTPException(
            status_code=400,
            detail="Provide either source_url or raw_content"
        )

    if post.source_url:
        try:
            response = httpx.get(
                post.source_url,
                timeout=10,
                follow_redirects=True
            )
            response.raise_for_status()
        except httpx.RequestError:
            raise HTTPException(
                status_code=400,
                detail="Could not fetch the provided URL"
            )
        except httpx.HTTPStatusError:
            raise HTTPException(
                status_code=400,
                detail="The provided URL could not be accessed"
            )

        content = clean_html(response.text)
    else:
        content = post.raw_content

    new_post = Post(
        source_url=post.source_url,
        raw_content=content
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return {
        "id": new_post.id,
        "source_url": new_post.source_url,
        "created_at": new_post.created_at
    }


@app.get("/posts")
def get_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(Post.created_at.desc()).all()

    return [
        {
            "id": post.id,
            "source_url": post.source_url,
            "created_at": post.created_at
        }
        for post in posts
    ]
    
    
@app.get("/posts/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db)):

    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    return {
        "id": post.id,
        "source_url": post.source_url,
        "raw_content": post.raw_content,
        "created_at": post.created_at
    }
    

@app.post("/posts/{post_id}/variants", status_code=201)
def create_variant(
    post_id: int,
    variant: VariantCreate,
    db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    new_variant = Variant(
        post_id=post_id,
        platform=variant.platform,
        content=variant.content,
        status="draft"
    )

    db.add(new_variant)
    db.commit()
    db.refresh(new_variant)

    return {
        "id": new_variant.id,
        "post_id": new_variant.post_id,
        "platform": new_variant.platform,
        "content": new_variant.content,
        "status": new_variant.status,
        "created_at": new_variant.created_at
    }
    
    
@app.get("/posts/{post_id}/variants")
def get_variants(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    variants = (
        db.query(Variant)
        .filter(Variant.post_id == post_id)
        .order_by(Variant.created_at.desc())
        .all()
    )

    return [
        {
            "id": variant.id,
            "post_id": variant.post_id,
            "platform": variant.platform,
            "content": variant.content,
            "status": variant.status,
            "created_at": variant.created_at
        }
        for variant in variants
    ]
    

@app.post("/posts/{post_id}/generate", status_code=201)
def generate_variant(
    post_id: int,
    variant: VariantGenerate,
    db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    prompt = f"""
Create a social media post for {variant.platform} based on the following content:

{post.raw_content}

Write only the final social media post.
"""
    
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
    except APIError:
        raise HTTPException(
            status_code=502,
            detail="AI service is currently unavailable"
        )

    generated_content = response.text
    
    new_variant = Variant(
        post_id=post_id,
        platform=variant.platform,
        content=generated_content,
        status="draft"
    )

    db.add(new_variant)
    db.commit()
    db.refresh(new_variant)

    return {
        "id": new_variant.id,
        "post_id": new_variant.post_id,
        "platform": new_variant.platform,
        "content": new_variant.content,
        "status": new_variant.status,
        "created_at": new_variant.created_at
    }