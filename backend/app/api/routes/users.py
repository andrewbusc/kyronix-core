from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, require_write_access
from app.core.roles import EmploymentStatus, RoleEnum
from app.core.security import get_password_hash
from app.db.models.user import User
from app.schemas.auth import PasswordResetResponse
from app.schemas.user import AdminPasswordReset, UserCreate, UserRead, UserSelfUpdate, UserUpdate

router = APIRouter()


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    try:
        hashed_password = get_password_hash(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    user = User(
        email=payload.email,
        hashed_password=hashed_password,
        legal_first_name=payload.legal_first_name,
        legal_last_name=payload.legal_last_name,
        preferred_name=payload.preferred_name,
        job_title=payload.job_title,
        department=payload.department,
        hire_date=payload.hire_date,
        phone=payload.phone,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        state=payload.state,
        postal_code=payload.postal_code,
        country=payload.country,
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
        emergency_contact_relationship=payload.emergency_contact_relationship,
        role=payload.role,
        employment_status=payload.employment_status,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    return db.query(User).order_by(User.id).all()


@router.patch("/me", response_model=UserRead)
def update_my_profile(
    payload: UserSelfUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_access),
):
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if current_user.id == user_id:
        if payload.role is not None and payload.role != user.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own role",
            )
        if payload.employment_status is not None and payload.employment_status != user.employment_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own employment status",
            )
        if payload.is_active is not None and payload.is_active != user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own active status",
            )

    if payload.email and payload.email != user.email:
        existing = (
            db.query(User)
            .filter(User.email == payload.email, User.id != user_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already exists"
            )
        user.email = payload.email

    update_data = payload.model_dump(exclude_unset=True)
    update_data.pop("email", None)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access")

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account"
        )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.delete(user)
    db.commit()


@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse)
def reset_user_password(
    user_id: int,
    payload: AdminPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        user.hashed_password = get_password_hash(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.add(user)
    db.commit()

    return PasswordResetResponse(message="Password reset successfully.")
