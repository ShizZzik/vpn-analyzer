from datetime import datetime
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_key = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to traffic data
    traffic_data = db.relationship('TrafficData', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.name or self.public_key[:8]}>'

class TrafficData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    received_bytes = db.Column(db.BigInteger, default=0)
    sent_bytes = db.Column(db.BigInteger, default=0)
    endpoint = db.Column(db.String(120), nullable=True)
    
    def __repr__(self):
        return f'<TrafficData {self.user_id} at {self.timestamp}>'