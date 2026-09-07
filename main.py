from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
import httpx

from database import Post, get_db
from schemas import PostCreate


app = FastAPI()


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

        content = response.text
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