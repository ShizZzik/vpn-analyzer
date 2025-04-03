from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from wtforms import Form, StringField, validators
import re

app = Flask(__name__)
app.config.from_object('config.Config')
db = SQLAlchemy(app)

# Import models after db initialization
from models import User, TrafficData

class UserForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=64)])
    email = StringField('Email', [validators.Email(), validators.Optional()])

def parse_wg_dump(dump_text):
    """
    Parse the output of 'wg show all dump' and return a dictionary of users with their traffic data.
    
    The dump format is:
    interface, public-key, private-key, listen-port, fwmark
    peer, public-key, preshared-key, endpoint, allowed-ips, latest-handshake, transfer-rx, transfer-tx, persistent-keepalive
    """
    lines = dump_text.split('\n')
    if not lines:
        return {}
    
    # Skip the first line (interface info)
    peer_lines = [line for line in lines[1:] if line.strip()]
    
    users = {}
    for line in peer_lines:
        parts = line.split('\t')
        if len(parts) < 8:
            continue
            
        public_key = parts[1]
        endpoint = parts[3]
        received_bytes = int(parts[6])
        sent_bytes = int(parts[7])
        
        if public_key not in users:
            users[public_key] = {
                'endpoint': endpoint,
                'received_bytes': received_bytes,
                'sent_bytes': sent_bytes
            }
        else:
            # Update if this entry has more recent data
            users[public_key]['received_bytes'] = max(users[public_key]['received_bytes'], received_bytes)
            users[public_key]['sent_bytes'] = max(users[public_key]['sent_bytes'], sent_bytes)
            users[public_key]['endpoint'] = endpoint
    
    return users

@app.route('/')
def dashboard():
    # Get all users with their latest traffic data
    users = User.query.all()
    
    user_data = []
    for user in users:
        latest_traffic = user.traffic_data.order_by(TrafficData.timestamp.desc()).first()
        if latest_traffic:
            user_data.append({
                'user': user,
                'received': latest_traffic.received_bytes,
                'sent': latest_traffic.sent_bytes,
                'endpoint': latest_traffic.endpoint,
                'last_seen': latest_traffic.timestamp
            })
    
    return render_template('dashboard.html', users=user_data)

@app.route('/user/<int:user_id>')
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    traffic_data = user.traffic_data.order_by(TrafficData.timestamp.desc()).limit(100).all()
    
    # Calculate total traffic
    total_received = sum(t.received_bytes for t in traffic_data)
    total_sent = sum(t.sent_bytes for t in traffic_data)
    
    return render_template('user_detail.html', 
                         user=user, 
                         traffic_data=traffic_data,
                         total_received=total_received,
                         total_sent=total_sent)

@app.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(request.form, obj=user)
    
    if request.method == 'POST' and form.validate():
        form.populate_obj(user)
        db.session.commit()
        return redirect(url_for('user_detail', user_id=user.id))
    
    return render_template('edit_user.html', form=form, user=user)

@app.route('/update', methods=['GET', 'POST'])
def update_data():
    if request.method == 'POST':
        dump_text = request.form.get('dump_text')
        if not dump_text:
            return render_template('update.html', error="No data provided")
        
        users_data = parse_wg_dump(dump_text)
        
        for public_key, data in users_data.items():
            # Find or create user
            user = User.query.filter_by(public_key=public_key).first()
            if not user:
                user = User(public_key=public_key)
                db.session.add(user)
                db.session.commit()
            
            # Create new traffic record
            traffic = TrafficData(
                user_id=user.id,
                received_bytes=data['received_bytes'],
                sent_bytes=data['sent_bytes'],
                endpoint=data['endpoint']
            )
            db.session.add(traffic)
        
        db.session.commit()
        return redirect(url_for('dashboard'))
    
    return render_template('update.html')

@app.cli.command('initdb')
def initdb_command():
    """Initialize the database."""
    db.create_all()
    print('Initialized the database.')

if __name__ == '__main__':
    app.run(debug=True)