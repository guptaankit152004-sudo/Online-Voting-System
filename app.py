from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# ----------------- Models -----------------
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))

class Voter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    has_voted = db.Column(db.Boolean, default=False)

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    votes = db.Column(db.Integer, default=0)
    photo = db.Column(db.String(100), nullable=False)       # filename of candidate photo
    party = db.Column(db.String(50), nullable=False)        # party name
    party_logo = db.Column(db.String(100), nullable=False)  # filename of party logo

# ----------------- Initialize DB and default candidates -----------------
with app.app_context():
    db.create_all()

    if Admin.query.count() == 0:
        default_admin = Admin(
            username="admin",
            password=generate_password_hash("admin123")
        )
        db.session.add(default_admin)
        db.session.commit()
        print("Default admin created: username='admin', password='admin123'")    

    # Add default candidates if not exist
    if Candidate.query.count() == 0:
        c1 = Candidate(
            name="Priya Verma",
            photo="priya_verma.jpg",
            party="BJP",
            party_logo="bjp_logo.png"
        )
        c2 = Candidate(
            name="Sheetal Yadav",
            photo="sheetal_yadav.jpg",
            party="Congress",
            party_logo="congress_logo.png"
        )
        db.session.add_all([c1, c2])
        db.session.commit()
        print("Default candidates added.")


# ----------------- Home -----------------
@app.route('/')
def home():
    return render_template('home.html')

# ----------------- Admin Routes -----------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['admin'] = admin.username
            return redirect('/admin/dashboard')
        else:
            flash("Invalid credentials")
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' in session:
        candidates = Candidate.query.all()
        total_voters = Voter.query.count()
        total_votes = sum([c.votes for c in candidates])
        return render_template('admin_dashboard.html', candidates=candidates,
                               total_voters=total_voters, total_votes=total_votes)
    else:
        return redirect('/admin/login')


@app.route('/add_candidate', methods=['GET','POST'])
def add_candidate():
    if 'admin' not in session:
        return redirect('/admin/login')
    if request.method == 'POST':
        name = request.form['name']
        photo = request.form['photo']           # filename in static/
        party = request.form['party']
        party_logo = request.form['party_logo'] # filename in static/
        candidate = Candidate(name=name, photo=photo, party=party, party_logo=party_logo)
        db.session.add(candidate)
        db.session.commit()
        flash("Candidate added successfully")
        return redirect('/admin/dashboard')
    return render_template('add_candidate.html')

@app.route('/edit_candidate/<int:id>', methods=['GET','POST'])
def edit_candidate(id):
    if 'admin' not in session:
        return redirect('/admin/login')

    candidate = Candidate.query.get(id)
    if not candidate:
        flash("Candidate not found!")
        return redirect('/admin/dashboard')

    if request.method == 'POST':
        candidate.name = request.form['name']
        candidate.photo = request.form['photo']
        candidate.party = request.form['party']
        candidate.party_logo = request.form['party_logo']
        db.session.commit()
        flash("Candidate updated successfully")
        return redirect('/admin/dashboard')

    return render_template('add_candidate.html', candidate=candidate)


@app.route('/delete_candidate/<int:id>')
def delete_candidate(id):
    if 'admin' not in session:
        return redirect('/admin/login')
    candidate = Candidate.query.get(id)
    db.session.delete(candidate)
    db.session.commit()
    flash("Candidate deleted successfully")
    return redirect('/admin/dashboard')

# ----------------- Voter Routes -----------------
@app.route('/voter/register', methods=['GET','POST'])
def voter_register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        voter = Voter(username=username, password=password)
        db.session.add(voter)
        db.session.commit()
        flash("Registration successful")
        return redirect('/voter/login')
    return render_template('voter_register.html')

@app.route('/voter/login', methods=['GET','POST'])
def voter_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        voter = Voter.query.filter_by(username=username).first()
        if voter and check_password_hash(voter.password, password):
            session['voter'] = voter.username
            session['voter_voted'] = voter.has_voted
            return redirect('/voter/dashboard')
        else:
            flash("Invalid credentials")
    return render_template('voter_login.html')

@app.route('/voter/dashboard')
def voter_dashboard():
    if 'voter' in session:
        candidates = Candidate.query.all()
        return render_template('voter_dashboard.html', candidates=candidates)
    else:
        return redirect('/voter/login')

@app.route('/vote/<int:candidate_id>')
def vote(candidate_id):
    if 'voter' not in session:
        return redirect('/voter/login')

    voter = Voter.query.filter_by(username=session['voter']).first()
    if not voter:
        flash("Voter not found!")
        return redirect('/voter/login')

    if voter.has_voted:
        flash("You have already voted!")
        session['voter_voted'] = True
        return redirect('/voter/dashboard')

    candidate = Candidate.query.get(candidate_id)
    if not candidate:
        flash("Candidate not found!")
        return redirect('/voter/dashboard')

    # Increment vote
    candidate.votes += 1
    voter.has_voted = True
    db.session.commit()

    flash(f"Vote cast successfully for {candidate.name}")
    session['voter_voted'] = True
    return redirect('/voter/dashboard')

# ----------------- Results Route -----------------
@app.route('/results')
def results():
    candidates = Candidate.query.all()  # Get all candidates
    return render_template('results.html', candidates=candidates)

# ----------------- Logout -----------------
@app.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('voter', None)
    flash("Logged out successfully")
    return redirect('/')

# ----------------- Run App -----------------
if __name__ == '__main__':
    app.run(debug=True)
