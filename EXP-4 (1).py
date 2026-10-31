import tkinter as tk
from tkinter import ttk, messagebox

inventory = {}


def get_form_data():
    code = code_var.get().strip().upper()
    name = name_var.get().strip()

    if not code or not name:
        messagebox.showerror("Invalid input", "Enter an item code and name.")
        return None

    try:
        quantity = int(quantity_var.get())
        price = float(price_var.get())
    except ValueError:
        messagebox.showerror(
            "Invalid input",
            "Quantity must be a whole number and price must be a number."
        )
        return None

    if quantity < 0 or price < 0:
        messagebox.showerror(
            "Invalid input",
            "Quantity and price cannot be negative."
        )
        return None

    return code, name, quantity, price


def refresh_table(items=None):
    for row in table.get_children():
        table.delete(row)

    records = inventory.items() if items is None else items
    total_value = 0

    for code, item in records:
        value = item["quantity"] * item["price"]
        total_value += value

        tag = "low_stock" if item["quantity"] < 5 else ""
        table.insert(
            "",
            tk.END,
            values=(
                code,
                item["name"],
                item["quantity"],
                f"{item['price']:.2f}",
                f"{value:.2f}"
            ),
            tags=(tag,)
        )

    total_var.set(f"Displayed stock value: ₹{total_value:.2f}")


def add_item():
    data = get_form_data()
    if data is None:
        return

    code, name, quantity, price = data

    if code in inventory:
        messagebox.showerror("Duplicate item", "This item code already exists.")
        return

    inventory[code] = {
        "name": name,
        "quantity": quantity,
        "price": price
    }

    refresh_table()
    clear_form()
    messagebox.showinfo("Success", "Item added successfully.")


def update_item():
    data = get_form_data()
    if data is None:
        return

    code, name, quantity, price = data

    if code not in inventory:
        messagebox.showerror("Item not found", "Select an existing item to update.")
        return

    inventory[code] = {
        "name": name,
        "quantity": quantity,
        "price": price
    }

    refresh_table()
    clear_form()
    messagebox.showinfo("Success", "Item updated successfully.")


def delete_item():
    code = code_var.get().strip().upper()

    if code not in inventory:
        messagebox.showerror("Item not found", "Select an item to delete.")
        return

    if messagebox.askyesno("Confirm deletion", f"Delete item {code}?"):
        del inventory[code]
        refresh_table()
        clear_form()


def search_item():
    query = search_var.get().strip().lower()

    if not query:
        refresh_table()
        return

    matches = [
        (code, item)
        for code, item in inventory.items()
        if query in code.lower() or query in item["name"].lower()
    ]

    refresh_table(matches)

    if not matches:
        messagebox.showinfo("Search result", "No matching items found.")


def show_low_stock():
    low_stock = [
        (code, item)
        for code, item in inventory.items()
        if item["quantity"] < 5
    ]
    refresh_table(low_stock)


def clear_form():
    code_var.set("")
    name_var.set("")
    quantity_var.set("")
    price_var.set("")
    code_entry.focus()


def select_item(event):
    selected = table.selection()
    if not selected:
        return

    values = table.item(selected[0], "values")
    code_var.set(values[0])
    name_var.set(values[1])
    quantity_var.set(values[2])
    price_var.set(values[3])


# -------------------- Main window --------------------

root = tk.Tk()
root.title("Inventory Tracker")
root.geometry("850x600")
root.minsize(750, 500)

code_var = tk.StringVar()
name_var = tk.StringVar()
quantity_var = tk.StringVar()
price_var = tk.StringVar()
search_var = tk.StringVar()
total_var = tk.StringVar(value="Displayed stock value: ₹0.00")

# Main Heading
title = ttk.Label(
    root,
    text="Inventory Tracker",
    font=("Arial", 20, "bold")
)
title.pack(pady=(15, 5))

# Student Details
student_details = ttk.Label(
    root,
    text="Name: P Madhan Mohan Reddy   |   Enrollment No: 92500115162   |   Branch: CSE-AI&DS (PBL)",
    font=("Arial", 10, "bold"),
    foreground="#1f4e79"
)
student_details.pack(pady=(0, 12))
form = ttk.LabelFrame(root, text="Item Details", padding=15)
form.pack(fill="x", padx=20, pady=5)

ttk.Label(form, text="Item Code").grid(row=0, column=0, sticky="w", pady=5)
code_entry = ttk.Entry(form, textvariable=code_var, width=25)
code_entry.grid(row=0, column=1, padx=10, pady=5)

ttk.Label(form, text="Item Name").grid(row=0, column=2, sticky="w", pady=5)
ttk.Entry(form, textvariable=name_var, width=30).grid(
    row=0, column=3, padx=10, pady=5
)

ttk.Label(form, text="Quantity").grid(row=1, column=0, sticky="w", pady=5)
ttk.Entry(form, textvariable=quantity_var, width=25).grid(
    row=1, column=1, padx=10, pady=5
)

ttk.Label(form, text="Unit Price (₹)").grid(row=1, column=2, sticky="w", pady=5)
ttk.Entry(form, textvariable=price_var, width=30).grid(
    row=1, column=3, padx=10, pady=5
)

button_frame = ttk.Frame(root)
button_frame.pack(pady=10)

ttk.Button(button_frame, text="Add", command=add_item).grid(
    row=0, column=0, padx=5
)
ttk.Button(button_frame, text="Update", command=update_item).grid(
    row=0, column=1, padx=5
)
ttk.Button(button_frame, text="Delete", command=delete_item).grid(
    row=0, column=2, padx=5
)
ttk.Button(button_frame, text="Clear Form", command=clear_form).grid(
    row=0, column=3, padx=5
)

search_frame = ttk.Frame(root)
search_frame.pack(fill="x", padx=20, pady=10)

ttk.Label(search_frame, text="Search by code or name:").pack(side="left")
ttk.Entry(search_frame, textvariable=search_var, width=25).pack(
    side="left", padx=8
)
ttk.Button(search_frame, text="Search", command=search_item).pack(
    side="left", padx=3
)
ttk.Button(search_frame, text="Show All", command=refresh_table).pack(
    side="left", padx=3
)
ttk.Button(search_frame, text="Low Stock", command=show_low_stock).pack(
    side="left", padx=3
)

table_frame = ttk.Frame(root)
table_frame.pack(fill="both", expand=True, padx=20, pady=5)

columns = ("code", "name", "quantity", "price", "value")
table = ttk.Treeview(
    table_frame,
    columns=columns,
    show="headings",
    selectmode="browse"
)

headings = {
    "code": "Item Code",
    "name": "Item Name",
    "quantity": "Quantity",
    "price": "Unit Price (₹)",
    "value": "Stock Value (₹)"
}

for column, heading in headings.items():
    table.heading(column, text=heading)

table.column("code", width=110, anchor="center")
table.column("name", width=240)
table.column("quantity", width=100, anchor="center")
table.column("price", width=130, anchor="e")
table.column("value", width=140, anchor="e")

table.tag_configure("low_stock", background="#ffe2e2")
table.bind("<<TreeviewSelect>>", select_item)

scrollbar = ttk.Scrollbar(
    table_frame,
    orient="vertical",
    command=table.yview
)
table.configure(yscrollcommand=scrollbar.set)

table.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

ttk.Label(
    root,
    textvariable=total_var,
    font=("Arial", 11, "bold")
).pack(anchor="e", padx=25, pady=(5, 15))

code_entry.focus()
root.mainloop()