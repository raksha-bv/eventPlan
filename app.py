from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify, make_response
from flask_login import UserMixin, login_user, logout_user, current_user, LoginManager
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from functools import wraps
from sqlalchemy import and_
import cloudinary
import cloudinary.uploader
import cloudinary.api


app=Flask(__name__,template_folder='templates')
config = cloudinary.config(secure=True)
app.config['SQLALCHEMY_DATABASE_URI']='mysql+mysqlconnector://root:S%40hil276@localhost/eventPlan2'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db = SQLAlchemy(app)
app.config['SECRET_KEY']='secret'
app.config['REMEMBER_COOKIE_DURATION']=timedelta(days=14)
app.config['REMEMBER_COOKIE_HTTPONLY']=True
app.config['REMEMBER_COOKIE_SECURE']=True
secret_key=secrets.token_hex(16)
app.secret_key=secret_key

login_manager=LoginManager()
login_manager.init_app(app)

favourite_items = db.Table(
    'favourite_items',
    db.Column('favorite_id', db.Integer, db.ForeignKey('favourite.id'), primary_key=True),
    db.Column('venue_id', db.Integer, db.ForeignKey('venues.id'), primary_key=True),
    # db.Column('venue_quantity', db.Integer, nullable=False, default=1)
)
booking_items = db.Table(
    'booking_items',
    db.Column('booking_id', db.Integer, db.ForeignKey('booking.id'), primary_key=True),
    db.Column('venue_id', db.Integer, db.ForeignKey('venues.id'), primary_key=True),
    # db.Column('venue_quantity', db.Integer, nullable=False, default=1)
)
class User(UserMixin, db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(250), nullable=False)
    email=db.Column(db.String(250), nullable=False)
    password=db.Column(db.String(250), nullable=False)
    is_admin=db.Column(db.Boolean, default=False, nullable=False)
    comments= db.relationship('Comment', backref='user')
    bookings= db.relationship('Booking', backref='user')
    favourites= db.relationship('Favourite', backref='user', uselist=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # venues_booked= db.relationship('Venues', secondary='order_items', backref='bookings')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date= db.Column(db.String(250), nullable=False)
    name= db.Column(db.String(250), nullable=False)
    email= db.Column(db.String(250), nullable=False)
    address1= db.Column(db.String(250), nullable=False)
    address2= db.Column(db.String(250), nullable=False)
    pincode= db.Column(db.Integer, nullable=False)
    town_city= db.Column(db.String(250), nullable=False)
    phone_number= db.Column(db.String(20), nullable=False)
    state= db.Column(db.String(250), nullable=False)
    country= db.Column(db.String(250), nullable=False)
    payment_type= db.Column(db.String(50), nullable=False)
    venue_title= db.Column(db.String(250), nullable=False)
    # venue_quantity= db.Column(db.Integer, nullable=False)
    venue_category= db.Column(db.String(250), nullable=False)

class Venues(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    category = db.Column(db.String(250), nullable=False)
    price = db.Column(db.String(250), nullable=False)
    image = db.Column(db.String(250), nullable=False)
    # quantity = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)
    favourites = db.relationship('Favourite', secondary='favourite_items', backref='venues', overlaps="favourites,venues")
    bookings = db.relationship('Booking', secondary='booking_items', backref='venues')

class Favourite(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    items = db.relationship('Venues', secondary=favourite_items, backref='favourite', overlaps="favourites,venues")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.route("/", methods=['POST', 'GET'])
def home():
    page = request.args.get('page', 1, type=int)
    per_page = 6
    venues = Venues.query.paginate(page=page, per_page=per_page, error_out=False)
    results = db.session.execute(db.select(User).order_by(User.name))
    users = results.scalars().all()
    return render_template("home.html", venues=venues, users=users)


@app.route("/reviews",methods=['POST', 'GET'])
def reviews():
    if request.method == "POST":
        new_comment = Comment(
            user_id=current_user.id,
            text=request.form.get('userComment')
        )
        db.session.add(new_comment)
        db.session.commit()
    results = db.session.execute(db.select(User).order_by(User.name))
    users = results.scalars().all()
    return render_template("comments.html",users=users)

@app.route('/admin/add_venue', methods=['POST', 'GET'])
@admin_only
def add_venue():
    if request.method == "POST":
        if 'image' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file:
            upload_result = cloudinary.uploader.upload(
                file,
                folder="venues"
            )
            image_url = upload_result.get('url')
        user_id = current_user.id
        new_venue = Venues(
            category=request.form.get('category'),
            price=request.form.get('price'),
            image=image_url,
            # quantity=request.form.get('quantity'),
            title=request.form.get('title'),
            user_id=user_id
        )

        db.session.add(new_venue)
        db.session.commit()
        return (redirect(url_for('home')))
    return render_template("venues_add_form.html")


@app.route('/admin/bookings', methods=['POST', 'GET'])
@admin_only
def all_bookings():
    admin_user_id=current_user.id
    bookings=  Booking.query.filter_by(admin_user_id).all()
    return render_template("bookings.html", bookings=bookings)

@app.route('/venue_details/<venue_id>', methods=['POST', 'GET'])
def venue_details(venue_id):
    if request.method == "POST":
        new_comment = Comment(
            user_id=current_user.id,
            text=request.form.get('userComment')
        )
        db.session.add(new_comment)
        db.session.commit()
    results = db.session.execute(db.select(User).order_by(User.name))
    users = results.scalars().all()
    venue = db.get_or_404(Venues, venue_id)
    # cancelled_price=int(venue.price)*10
    return render_template("venue_details.html", venue=venue, users=users)


@app.route("/add-to-favourite/<int:venue_id>")
def add_to_favourite(venue_id):
    if not current_user.is_authenticated:
        return render_template('not_log_in.html', message="You need to be logged in to add items to favourites")

    user = current_user
    venue = db.get_or_404(Venues, venue_id)

    if user.favourite is None:
        user.favourite = Favourite()
        db.session.commit()

    user_favourite= user.favourite
    favourite_item= db.session.query(favourite_items).filter_by(favourite_id=user_favourite.id, venue_id=venue.id).first()

    if favourite_item is None:
        db.session.execute(favourite_items.insert().values(favourite_id=user_favourite.id, venue_id=venue.id, venue_quantity=1))
    else:
        db.session.execute(
            favourite_items.update().where(favourite_items.c.favourite_id == user_favourite.id, favourite_items.c.venue_id == venue.id).values(
                venue_quantity=favourite_item.cover_quantity + 1))
    if venue not in user_favourite.items:
        user_favourite.items.append(venue)

    db.session.commit()
    return redirect(url_for('home'))

@app.route("/view_favourite")
def view_favourite():
    if not current_user.is_authenticated:
        return render_template('not_log_in.html', message="You need to be logged in to access your favourites")

    user = current_user
    user_favourite = user.favourite

    if user_favourite is None:
        user_favourite = Favourite(user_id=user.id)
        db.session.add(user_favourite)
        db.session.commit()

    user_favourite_items = user_favourite.items
    total = 0
    items = []

    for item in user_favourite_items:
        favourite_item = db.session.query(favourite_items).filter_by(favourite_id=user_favourite.id, venue_id=item.id).first()
        venue_item = {
            'venue': item,
            'venue_quantity': favourite_item.venue_quantity if favourite_item else 0,
            'image': item.image,
            'price': item.price,
            'title': item.title,
            'category': item.category,
            'id': item.id
        }
        items.append(venue_item)
        total += int(item.price.split('.')[0]) * venue_item['venue_quantity']

    return render_template("favourite.html", items=items, total=total)
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method== 'POST':
        results = db.session.execute(db.select(User).where(User.email == request.form.get('email')))
        user = results.scalar()
        if user:
            password = request.form.get('password')
            if (check_password_hash(user.password, password)):
                login_user(user)
                return redirect(url_for('home'))
            else:
                flash("Incorrect password")
        else:
            flash('No account found with that Email address. Please register.')
    return render_template("login_form.html")

@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method =='POST':
        results = db.session.execute(db.select(User).where(User.email == request.form.get('email')))
        user = results.scalar()
        if not user:
            if request.form.get('role')=='customer':
                planner=False
            else:
                planner=True
            new_user = User(
                name=request.form.get('username'),
                email=request.form.get('email'),
                password=generate_password_hash(request.form.get('password')),
                is_admin=planner
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('home'))
        else:
            flash(f"An account is already registered to this email.")
    return render_template('signup_form.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/search_venues/')
def search_venues():
    s = request.args.get('query', '')
    results = Venues.query.filter(Venues.title.ilike(f"%{s}%")).all()
    return render_template('results.html', results=results, query=s)


@app.route('/about-us')
def about_us():
    return render_template("about.html")

@app.route('/account')
def account():
    if current_user.is_authenticated:
        bookings = Booking.query.filter_by(user_id=current_user.id).all()
        return render_template("account.html", user=current_user, items=bookings)
    else:
        return render_template("not_log_in.html", message="You need to be logged in to check your account")

@app.route('/checkout', methods=['POST', 'GET'])
def checkout():
    if request.method == 'POST':
        user = current_user
        venues_info = []
        for item in user.favourite.items:
            favourite_it = db.session.query(favourite_items).filter_by(favourite_id=user.favourite.id, venue_id=item.id).first()
            venue_info={
                'venue': item,
                'quantity': favourite_it.venue_quantity,
                'price': item.price,
                'title': item.title,
                'category': item.category,
            }
            venues_info.append(venues_info)

        for venue in venues_info:
            new_booking = Booking(
                user_id=current_user.id,
                date=str(datetime.today().date()),
                name=request.form.get('name'),
                email=request.form.get('email'),
                address1=request.form.get('address1'),
                address2=request.form.get('address2'),
                pincode=request.form.get('pincode'),
                town_city=request.form.get('Town/City'),
                phone_number=request.form.get('phone'),
                state=request.form.get('state'),
                country=request.form.get('countries'),
                payment_type=request.form.get('payment_type'),
                venue_title=venue['title'],
                venue_quantity=venue['quantity'],
                venue_category=venue['model']
            )
        db.session.add(new_booking)

        for item in user.favourite.items:
            favourite_it = db.session.query(favourite_items).filter_by(favourite_id=user.favourite.id, venue_id=item.id).first()
            if favourite_it:
                item.booking_id = new_booking.id
                cover = db.session.get(Venues, item.id)
                cover.quantity -= favourite_it.cover_quantity
                db.session.query(favourite_items).filter_by(favourite_id=user.favourite.id, favourites_id=item.id).delete()
                db.session.commit()

        user.favourite.items = []
        db.session.commit()
        return render_template("order_sucess.html")

    user = current_user
    if not current_user.is_authenticated or user.favourite is None:
        return render_template("not_log_in.html", message='Session Expired! Please Log In Again')

    user_favourite = user.favourtie
    user_favourite_items = user_favourite.items
    total = 0
    items = []

    for item in user_favourite_items:
        favourite_item = db.session.query(favourite_items).filter_by(favourite_id=user_favourite.id, venue_id=item.id).first()
        venue_item = {
            'venue': item,
            'venue_quantity': favourite_item.venue_quantity,
            'image': item.image,
            'price': item.price,
            'title': item.title,
            'category': item.category,
            'id': item.id
        }
        items.append(venue_item)
        total += int(item.price.split('.')[0]) * venue_item['venue_quantity']
    return render_template("checkout.html", items=items, total=total)


if __name__ == "__main__":
    app.run(debug=True)