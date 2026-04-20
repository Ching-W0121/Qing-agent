from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.user import UserCreate, UserResponse, UserProfileUpdate

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(
        auth0_id=user.auth0_id,
        email=user.email,
        username=user.username
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}/profile", response_model=UserResponse)
def update_profile(user_id: int, profile: UserProfileUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.profile:
        user.profile = UserProfile(user_id=user_id)

    update_data = profile.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user.profile, key, value)

    db.commit()
    db.refresh(user)
    return user
