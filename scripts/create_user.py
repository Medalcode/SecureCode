import argparse
import sys
import getpass
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import os
# Adjust path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from securecode.adapters.postgres.models import User
from securecode.api.security import hash_password

def main():
    parser = argparse.ArgumentParser(description="SecureCode User Provisioning")
    parser.add_argument("--username", required=True, help="Username to create")
    args = parser.parse_args()
    
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
        
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    existing = session.query(User).filter_by(username=args.username).first()
    if existing:
        print(f"ERROR: Username '{args.username}' already exists")
        sys.exit(1)
        
    password = getpass.getpass("Enter password: ")
    if not password or len(password) < 8:
        print("ERROR: Password must be at least 8 characters")
        sys.exit(1)
        
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("ERROR: Passwords do not match")
        sys.exit(1)
        
    user = User(
        id=uuid4(),
        username=args.username,
        password_hash=hash_password(password),
        active=True,
        created_at=datetime.now(timezone.utc)
    )
    session.add(user)
    session.commit()
    print(f"User '{args.username}' successfully provisioned.")

if __name__ == "__main__":
    main()
