from models.models import Article
from sqlalchemy.orm import Session
from database.database import SessionLocal

def remove_partial_duplicate_articles():
    db: Session = SessionLocal()
    try:
        articles = db.query(Article).all()
        seen_titles = set()
        seen_contents = set()
        to_delete = []


        for article in articles:
            is_duplicate = (
                article.news_title in seen_titles or
                article.news_content in seen_contents
            )

            if is_duplicate:
                to_delete.append(article)
            else:
                seen_titles.add(article.news_title)
                seen_contents.add(article.news_content)

        for article in to_delete:
            db.delete(article)

        db.commit()
        print(f"중복 기사 {len(to_delete)}건 삭제 완료.")
    except Exception as e:
        db.rollback()
        print(f"오류 발생: {e}")
    finally:
        db.close()
