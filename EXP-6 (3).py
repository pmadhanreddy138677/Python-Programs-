import tkinter as tk
from tkinter import ttk, messagebox


# --------------------------------------------------
# BankAccount class
# --------------------------------------------------

class BankAccount:

    def __init__(self, account_no, holder, opening_balance=0):
        self.account_no = account_no
        self.holder = holder

        # Private balance variable
        self.__balance = opening_balance

        # Store account transactions
        self.transactions = [
            ("OPEN", opening_balance, self.__balance)
        ]

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")

        self.__balance += amount

        self.transactions.append(
            ("DEPOSIT", amount, self.__balance)
        )

    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")

        if amount > self.__balance:
            raise ValueError("Insufficient balance.")

        self.__balance -= amount

        self.transactions.append(
            ("WITHDRAW", amount, self.__balance)
        )

    def balance(self):
        return self.__balance


# The account object will be created through the UI
account = None


# --------------------------------------------------
# Create account
# --------------------------------------------------

def create_account():
    global account

    account_no = account_no_var.get().strip().upper()
    holder = holder_var.get().strip()

    if not account_no:
        messagebox.showerror(
            "Invalid Input",
            "Enter the account number."
        )
        return

    if not holder:
        messagebox.showerror(
            "Invalid Input",
            "Enter the account holder's name."
        )
        return

    try:
        opening_balance = float(
            opening_balance_var.get()
        )
    except ValueError:
        messagebox.showerror(
            "Invalid Input",
            "Opening balance must be a number."
        )
        return

    if opening_balance < 0:
        messagebox.showerror(
            "Invalid Input",
            "Opening balance cannot be negative."
        )
        return

    account = BankAccount(
        account_no,
        holder,
        opening_balance
    )

    account_status_var.set(
        f"Account created: {account_no} - {holder}"
    )

    amount_var.set("")
    update_account_display()

    messagebox.showinfo(
        "Account Created",
        "Bank account created successfully."
    )


# --------------------------------------------------
# Deposit money
# --------------------------------------------------

def deposit_money():
    if account is None:
        messagebox.showerror(
            "Account Not Created",
            "Please create an account first."
        )
        return

    try:
        amount = float(amount_var.get())
        account.deposit(amount)

        amount_var.set("")
        update_account_display()

        messagebox.showinfo(
            "Deposit Successful",
            f"₹{amount:.2f} deposited successfully."
        )

    except ValueError as error:
        messagebox.showerror(
            "Deposit Error",
            str(error)
        )


# --------------------------------------------------
# Withdraw money
# --------------------------------------------------

def withdraw_money():
    if account is None:
        messagebox.showerror(
            "Account Not Created",
            "Please create an account first."
        )
        return

    try:
        amount = float(amount_var.get())
        account.withdraw(amount)

        amount_var.set("")
        update_account_display()

        messagebox.showinfo(
            "Withdrawal Successful",
            f"₹{amount:.2f} withdrawn successfully."
        )

    except ValueError as error:
        messagebox.showerror(
            "Withdrawal Error",
            str(error)
        )


# --------------------------------------------------
# Display current balance
# --------------------------------------------------

def show_balance():
    if account is None:
        messagebox.showerror(
            "Account Not Created",
            "Please create an account first."
        )
        return

    messagebox.showinfo(
        "Current Balance",
        f"Account Number: {account.account_no}\n"
        f"Account Holder: {account.holder}\n"
        f"Current Balance: ₹{account.balance():.2f}"
    )


# --------------------------------------------------
# Update balance and transaction table
# --------------------------------------------------

def update_account_display():
    if account is None:
        balance_var.set("Current Balance: ₹0.00")
        return

    balance_var.set(
        f"Current Balance: ₹{account.balance():.2f}"
    )

    # Delete the old rows from the table
    for row in transaction_table.get_children():
        transaction_table.delete(row)

    # Add updated transactions
    for transaction_number, transaction in enumerate(
        account.transactions,
        start=1
    ):
        transaction_type = transaction[0]
        amount = transaction[1]
        balance_after_transaction = transaction[2]

        transaction_table.insert(
            "",
            tk.END,
            values=(
                transaction_number,
                transaction_type,
                f"{amount:.2f}",
                f"{balance_after_transaction:.2f}"
            ),
            tags=(transaction_type,)
        )


# --------------------------------------------------
# Clear transaction amount
# --------------------------------------------------

def clear_amount():
    amount_var.set("")
    amount_entry.focus()


# --------------------------------------------------
# Reset the entire application
# --------------------------------------------------

def reset_application():
    global account

    confirmation = messagebox.askyesno(
        "Reset Application",
        "Do you want to delete the current account data?"
    )

    if confirmation:
        account = None

        account_no_var.set("AC101")
        holder_var.set("Riya")
        opening_balance_var.set("5000")
        amount_var.set("")

        account_status_var.set(
            "No account has been created."
        )

        balance_var.set(
            "Current Balance: ₹0.00"
        )

        for row in transaction_table.get_children():
            transaction_table.delete(row)


# --------------------------------------------------
# Create the main window
# --------------------------------------------------

root = tk.Tk()
root.title("Bank Account Management System")
root.geometry("850x650")
root.minsize(750, 580)


# --------------------------------------------------
# Tkinter variables
# --------------------------------------------------

account_no_var = tk.StringVar(value="AC101")
holder_var = tk.StringVar(value="Riya")
opening_balance_var = tk.StringVar(value="5000")
amount_var = tk.StringVar()

account_status_var = tk.StringVar(
    value="No account has been created."
)

balance_var = tk.StringVar(
    value="Current Balance: ₹0.00"
)


# --------------------------------------------------
# Application title
# --------------------------------------------------

title_label = ttk.Label(
    root,
    text="Bank Account Management System",
    font=("Arial", 22, "bold")
)

title_label.pack(
    pady=(15, 5)
)

subtitle_label = ttk.Label(
    root,
    text="Name: P Madhan Mohan Reddy   |   Enrollment No: 92500115162   |   Branch: CSE-AI&DS (PBL)",
    font=("Arial", 11)
)

subtitle_label.pack(
    pady=(0, 15)
)


# --------------------------------------------------
# Account-details frame
# --------------------------------------------------

account_frame = ttk.LabelFrame(
    root,
    text="Create Account",
    padding=15
)

account_frame.pack(
    fill="x",
    padx=20,
    pady=5
)

ttk.Label(
    account_frame,
    text="Account Number"
).grid(
    row=0,
    column=0,
    sticky="w",
    padx=5,
    pady=5
)

account_no_entry = ttk.Entry(
    account_frame,
    textvariable=account_no_var,
    width=25
)

account_no_entry.grid(
    row=0,
    column=1,
    padx=5,
    pady=5
)

ttk.Label(
    account_frame,
    text="Account Holder"
).grid(
    row=0,
    column=2,
    sticky="w",
    padx=5,
    pady=5
)

holder_entry = ttk.Entry(
    account_frame,
    textvariable=holder_var,
    width=25
)

holder_entry.grid(
    row=0,
    column=3,
    padx=5,
    pady=5
)

ttk.Label(
    account_frame,
    text="Opening Balance (₹)"
).grid(
    row=1,
    column=0,
    sticky="w",
    padx=5,
    pady=5
)

opening_balance_entry = ttk.Entry(
    account_frame,
    textvariable=opening_balance_var,
    width=25
)

opening_balance_entry.grid(
    row=1,
    column=1,
    padx=5,
    pady=5
)

create_button = ttk.Button(
    account_frame,
    text="Create Account",
    command=create_account
)

create_button.grid(
    row=1,
    column=2,
    columnspan=2,
    padx=5,
    pady=5
)


# --------------------------------------------------
# Account-status labels
# --------------------------------------------------

status_label = ttk.Label(
    root,
    textvariable=account_status_var,
    font=("Arial", 11)
)

status_label.pack(
    pady=(10, 3)
)

balance_label = ttk.Label(
    root,
    textvariable=balance_var,
    font=("Arial", 18, "bold"),
    foreground="#006400"
)

balance_label.pack(
    pady=(3, 10)
)


# --------------------------------------------------
# Transaction frame
# --------------------------------------------------

transaction_frame = ttk.LabelFrame(
    root,
    text="Banking Transaction",
    padding=15
)

transaction_frame.pack(
    fill="x",
    padx=20,
    pady=5
)

ttk.Label(
    transaction_frame,
    text="Transaction Amount (₹)"
).grid(
    row=0,
    column=0,
    padx=5,
    pady=5
)

amount_entry = ttk.Entry(
    transaction_frame,
    textvariable=amount_var,
    width=25
)

amount_entry.grid(
    row=0,
    column=1,
    padx=5,
    pady=5
)

deposit_button = ttk.Button(
    transaction_frame,
    text="Deposit",
    command=deposit_money
)

deposit_button.grid(
    row=0,
    column=2,
    padx=5,
    pady=5
)

withdraw_button = ttk.Button(
    transaction_frame,
    text="Withdraw",
    command=withdraw_money
)

withdraw_button.grid(
    row=0,
    column=3,
    padx=5,
    pady=5
)

balance_button = ttk.Button(
    transaction_frame,
    text="Check Balance",
    command=show_balance
)

balance_button.grid(
    row=0,
    column=4,
    padx=5,
    pady=5
)

clear_button = ttk.Button(
    transaction_frame,
    text="Clear",
    command=clear_amount
)

clear_button.grid(
    row=0,
    column=5,
    padx=5,
    pady=5
)


# --------------------------------------------------
# Transaction-history table
# --------------------------------------------------

history_frame = ttk.LabelFrame(
    root,
    text="Transaction History",
    padding=10
)

history_frame.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=10
)

columns = (
    "number",
    "transaction",
    "amount",
    "balance"
)

transaction_table = ttk.Treeview(
    history_frame,
    columns=columns,
    show="headings",
    height=10
)

transaction_table.heading(
    "number",
    text="Sr. No."
)

transaction_table.heading(
    "transaction",
    text="Transaction Type"
)

transaction_table.heading(
    "amount",
    text="Amount (₹)"
)

transaction_table.heading(
    "balance",
    text="Balance (₹)"
)

transaction_table.column(
    "number",
    width=80,
    anchor="center"
)

transaction_table.column(
    "transaction",
    width=180,
    anchor="center"
)

transaction_table.column(
    "amount",
    width=150,
    anchor="e"
)

transaction_table.column(
    "balance",
    width=150,
    anchor="e"
)

# Row colours according to transaction type
transaction_table.tag_configure(
    "OPEN",
    background="#e6f2ff"
)

transaction_table.tag_configure(
    "DEPOSIT",
    background="#dff5e1"
)

transaction_table.tag_configure(
    "WITHDRAW",
    background="#ffe2e2"
)


# --------------------------------------------------
# Add scrollbar to the table
# --------------------------------------------------

history_scrollbar = ttk.Scrollbar(
    history_frame,
    orient="vertical",
    command=transaction_table.yview
)

transaction_table.configure(
    yscrollcommand=history_scrollbar.set
)

transaction_table.pack(
    side="left",
    fill="both",
    expand=True
)

history_scrollbar.pack(
    side="right",
    fill="y"
)


# --------------------------------------------------
# Bottom buttons
# --------------------------------------------------

bottom_frame = ttk.Frame(root)

bottom_frame.pack(
    pady=(0, 15)
)

reset_button = ttk.Button(
    bottom_frame,
    text="Reset Application",
    command=reset_application
)

reset_button.grid(
    row=0,
    column=0,
    padx=5
)

exit_button = ttk.Button(
    bottom_frame,
    text="Exit",
    command=root.destroy
)

exit_button.grid(
    row=0,
    column=1,
    padx=5
)


# Place the cursor in the account-number box
account_no_entry.focus()


# Start the Tkinter application
root.mainloop()