from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'expense_tracker_secret'

# CREATE DATABASE
def init_db():
    conn = sqlite3.connect('expense.db')
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    # Expenses table with user_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            amount REAL,
            type TEXT,
            category TEXT,
            date TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# LOGIN PAGE
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('expense.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user[0]  # store user id
            session['username'] = user[1]
            return redirect('/dashboard')
        else:
            error = 'Invalid username or password!'

    return render_template('login.html', error=error)
@app.route('/profile')
def profile():

    if 'user' not in session:
        return redirect('/')

    user_id = session['user']

    conn = sqlite3.connect('expense.db')
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM expenses WHERE user_id=? ORDER BY id DESC",
        (user_id,)
    )

    expenses = cursor.fetchall() 



    monthly_data ={}

   
     

    conn.close()

    total_income = 0
    total_expense = 0

    for item in expenses:

        if item[4] == "Income":
            total_income += float(item[3])

        if item[4] == "Expense":
            total_expense += float(item[3])

    balance = total_income - total_expense
    monthly_saving = balance

    budget = 20000
   
    goal = session.get('goal',5000)

    remaining_budget = budget - total_expense

    if goal > 0:
        goal_percent = (balance / goal) * 100
    else:
        goal_percent = 0


    return render_template(
        'profile.html',
        username=session['username'],
        income=total_income,
        expense=total_expense,
        balance=balance,
        transactions=len(expenses),
       
        monthly_saving=balance,
        expenses=expenses[:5],
        budget=budget,
        goal=goal,
        goal_percent=goal_percent,
        remaining_budget=remaining_budget,
       
        
    )
@app.route('/download_pdf')
def download_pdf():

    if 'user' not in session:
        return redirect('/')

    user_id = session['user']

    conn = sqlite3.connect('expense.db')
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM expenses WHERE user_id=? ORDER BY id DESC",
        (user_id,)
    )

    expenses = cursor.fetchall()

    conn.close()

    total_income = 0
    total_expense = 0

    for item in expenses:

        if item[4] == "Income":
            total_income += float(item[3])

        elif item[4] == "Expense":
            total_expense += float(item[3])

    balance = total_income - total_expense

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    elements = []

    title = Paragraph(
        "<b>EXPENSE TRACKER REPORT</b>",
        styles['Title']
    )

    elements.append(title)
    elements.append(Spacer(1, 12))

    elements.append(
        Paragraph(
            f"User: {session['username']}",
            styles['Normal']
        )
    )

    elements.append(
        Paragraph(
            f"Generated: {datetime.now().strftime('%d-%m-%Y')}",
            styles['Normal']
        )
    )

    elements.append(Spacer(1, 20))

    summary_data = [
        ["Total Income", f"₹ {total_income}"],
        ["Total Expense", f"₹ {total_expense}"],
        ["Balance", f"₹ {balance}"]
    ]

    summary_table = Table(summary_data, colWidths=[200, 150])

    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold')
    ]))

    elements.append(
        Paragraph(
            "<b>Financial Summary</b>",
            styles['Heading2']
        )
    )

    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    transaction_data = [
        ["Title", "Amount", "Type", "Category"]
    ]

    for item in expenses:

        transaction_data.append([
            str(item[2]),
            f"₹ {item[3]}",
            str(item[4]),
            str(item[5])
        ])

    transaction_table = Table(transaction_data)

    transaction_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
    ]))

    elements.append(
        Paragraph(
            "<b>Transaction History</b>",
            styles['Heading2']
        )
    )

    elements.append(transaction_table)

    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph(
            "Generated by Expense Tracker",
            styles['Italic']
        )
    )

    doc.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Expense_Report.pdf",
        mimetype='application/pdf'
    )
# REGISTER PAGE
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm']

        if password != confirm:
            error = 'Passwords do not match!'
        elif len(username) < 3:
            error = 'Username must be at least 3 characters!'
        elif len(password) < 4:
            error = 'Password must be at least 4 characters!'
        else:
            try:
                conn = sqlite3.connect('expense.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                conn.close()
                success = 'Account created! You can now login.'
            except sqlite3.IntegrityError:
                error = 'Username already exists!'

    return render_template('register.html', error=error, success=success)

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# DASHBOARD
@app.route('/dashboard')
def index():
    if 'user' not in session:
        return redirect('/')

    user_id = session['user']

    conn = sqlite3.connect('expense.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE user_id=? ORDER BY id DESC", (user_id,))
    expenses = cursor.fetchall()
    recent_transactions = expenses[:5]
    conn.close()

    category_totals = {}
    total_income = 0
    total_expense = 0

    for item in expenses:
        if item[4] == "Income":
            total_income += float(item[3])
        if item[4] == "Expense":
            total_expense += float(item[3])
            category = item[5]
            category_totals[category] = category_totals.get(category, 0) + float(item[3])

    balance = total_income - total_expense
    
    top_category = "no Expenses"
    top_amount = 0

    if len(category_totals) > 0:
        top_category = max(category_totals,key=category_totals.get)
        top_amount= category_totals[top_category]
    print(category_totals)


    return render_template(
        'index.html',
        expenses=expenses,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        recent_transactions=recent_transactions,
       top_category=top_category,
top_amount=top_amount,
        categories=list(category_totals.keys()),
        values=list(category_totals.values()),
        username=session['username']
    )

@app.route('/update_goal', methods=['POST'])
def update_goal():

    if 'user' not in session:
        return redirect('/')

    session['goal'] = int(request.form['goal'])

    return redirect('/profile')
# ADD TRANSACTION
@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session:
        return redirect('/')

    user_id = session['user']
    title = request.form['title']
    amount = request.form['amount']
    type_ = request.form['type']
    category = request.form['category']
    date = datetime.now().strftime('%Y-%m-%d')

    conn = sqlite3.connect('expense.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (user_id, title, amount, type, category, date) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, title, amount, type_, category, date)
    )
    conn.commit()
    conn.close()

    return redirect('/dashboard')

# EDIT TRANSACTION
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if 'user' not in session:
        return redirect('/')

    conn = sqlite3.connect('expense.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        title = request.form['title']
        amount = request.form['amount']
        type_ = request.form['type']
        category = request.form['category']
        cursor.execute(
            "UPDATE expenses SET title=?, amount=?, type=?, category=? WHERE id=? AND user_id=?",
            (title, amount, type_, category, id, session['user'])
        )
        conn.commit()
        conn.close()
        return redirect('/dashboard')

    cursor.execute("SELECT * FROM expenses WHERE id=? AND user_id=?", (id, session['user']))
    expense = cursor.fetchone()
    conn.close()

    if not expense:
        return redirect('/dashboard')

    return render_template('edit.html', expense=expense)

# DELETE TRANSACTION
@app.route('/delete/<int:id>')
def delete(id):
    if 'user' not in session:
        return redirect('/')

    conn = sqlite3.connect('expense.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (id, session['user']))
    conn.commit()
    conn.close()

    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(debug=True)
