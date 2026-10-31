import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import csv
import os
from collections import Counter


# Stores the selected log-file path
selected_file = ""

# Stores the latest analysis results
log_counts = Counter()
detected_errors = []


# --------------------------------------------------
# Function 1: Generate a sample log file
# --------------------------------------------------

def generate_sample_log():
    global selected_file

    selected_file = os.path.abspath("app.log")

    # Create a separate logger for this application
    logger = logging.getLogger("InventoryLogAnalyzer")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Remove old handlers to avoid duplicate log entries
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    # Create a file handler
    file_handler = logging.FileHandler(
        selected_file,
        mode="w",
        encoding="utf-8"
    )

    # Define the format of every log record
    formatter = logging.Formatter(
        "%(asctime)s|%(levelname)s|%(message)s"
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Generate sample log messages
    logger.info("Application started")
    logger.debug("User authentication module loaded")
    logger.warning("Memory usage above 75 percent")
    logger.error("Database connection failed")
    logger.critical("Server stopped unexpectedly")
    logger.info("Application stopped")

    # Flush and close the file handler
    file_handler.flush()
    file_handler.close()
    logger.removeHandler(file_handler)

    file_path_var.set(selected_file)

    messagebox.showinfo(
        "Log File Created",
        f"Sample log file created successfully.\n\n{selected_file}"
    )

    analyse_log_file()


# --------------------------------------------------
# Function 2: Select an existing log file
# --------------------------------------------------

def browse_log_file():
    global selected_file

    path = filedialog.askopenfilename(
        title="Select Log File",
        filetypes=[
            ("Log files", "*.log"),
            ("Text files", "*.txt"),
            ("All files", "*.*")
        ]
    )

    if path:
        selected_file = path
        file_path_var.set(selected_file)
        clear_results()


# --------------------------------------------------
# Function 3: Analyse the selected log file
# --------------------------------------------------

def analyse_log_file():
    global log_counts, detected_errors, selected_file

    # Read the path shown in the entry box
    selected_file = file_path_var.get().strip()

    if not selected_file:
        messagebox.showerror(
            "File Not Selected",
            "Please select or generate a log file."
        )
        return

    if not os.path.exists(selected_file):
        messagebox.showerror(
            "File Not Found",
            "The selected log file does not exist."
        )
        return

    log_counts = Counter()
    detected_errors = []
    malformed_lines = []

    try:
        with open(selected_file, "r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):

                # Expected format:
                # date and time | log level | message
                parts = line.strip().split("|", 2)

                if len(parts) == 3:
                    timestamp = parts[0].strip()
                    level = parts[1].strip().upper()
                    message = parts[2].strip()

                    log_counts[level] += 1

                    if level in ("ERROR", "CRITICAL"):
                        detected_errors.append(
                            (line_number, timestamp, level, message)
                        )
                else:
                    malformed_lines.append(
                        (line_number, line.strip())
                    )

    except PermissionError:
        messagebox.showerror(
            "Permission Error",
            "The selected file cannot be accessed."
        )
        return

    except UnicodeDecodeError:
        messagebox.showerror(
            "Encoding Error",
            "The selected file is not a valid UTF-8 text file."
        )
        return

    except OSError as error:
        messagebox.showerror(
            "File Error",
            f"Could not read the file.\n\n{error}"
        )
        return

    display_results(malformed_lines)

    messagebox.showinfo(
        "Analysis Completed",
        "The log file was analysed successfully."
    )


# --------------------------------------------------
# Function 4: Display analysis results
# --------------------------------------------------

def display_results(malformed_lines):
    clear_results()

    total_records = sum(log_counts.values())

    # Display the count of each log level
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        count = log_counts.get(level, 0)

        count_table.insert(
            "",
            tk.END,
            values=(level, count),
            tags=(level,)
        )

    total_records_var.set(f"Total valid log records: {total_records}")
    error_count_var.set(
        f"Errors and critical events: {len(detected_errors)}"
    )
    malformed_count_var.set(
        f"Malformed lines: {len(malformed_lines)}"
    )

    # Display detected errors
    error_text.config(state="normal")
    error_text.delete("1.0", tk.END)

    if detected_errors:
        for line_number, timestamp, level, message in detected_errors:
            error_text.insert(
                tk.END,
                f"Line: {line_number}\n"
                f"Time: {timestamp}\n"
                f"Level: {level}\n"
                f"Message: {message}\n"
                f"{'-' * 65}\n"
            )
    else:
        error_text.insert(
            tk.END,
            "No ERROR or CRITICAL messages were detected."
        )

    if malformed_lines:
        error_text.insert(
            tk.END,
            "\nMalformed Lines\n"
            f"{'=' * 65}\n"
        )

        for line_number, content in malformed_lines:
            error_text.insert(
                tk.END,
                f"Line {line_number}: {content}\n"
            )

    error_text.config(state="disabled")


# --------------------------------------------------
# Function 5: Export summary to a CSV file
# --------------------------------------------------

def export_summary():
    if not log_counts:
        messagebox.showerror(
            "No Results",
            "Analyse a log file before exporting the summary."
        )
        return

    output_path = filedialog.asksaveasfilename(
        title="Save Log Summary",
        defaultextension=".csv",
        initialfile="log_summary.csv",
        filetypes=[("CSV files", "*.csv")]
    )

    if not output_path:
        return

    try:
        with open(
            output_path,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow(["Log Level", "Count"])

            for level in [
                "DEBUG",
                "INFO",
                "WARNING",
                "ERROR",
                "CRITICAL"
            ]:
                writer.writerow([
                    level,
                    log_counts.get(level, 0)
                ])

            writer.writerow([])
            writer.writerow([
                "Total Valid Records",
                sum(log_counts.values())
            ])

            writer.writerow([
                "Errors and Critical Events",
                len(detected_errors)
            ])

            writer.writerow([])
            writer.writerow([
                "Line Number",
                "Timestamp",
                "Level",
                "Message"
            ])

            for record in detected_errors:
                writer.writerow(record)

        messagebox.showinfo(
            "Export Successful",
            f"Summary saved successfully.\n\n{output_path}"
        )

    except OSError as error:
        messagebox.showerror(
            "Export Error",
            f"Could not save the CSV file.\n\n{error}"
        )


# --------------------------------------------------
# Function 6: Clear displayed results
# --------------------------------------------------

def clear_results():
    for row in count_table.get_children():
        count_table.delete(row)

    error_text.config(state="normal")
    error_text.delete("1.0", tk.END)
    error_text.config(state="disabled")

    total_records_var.set("Total valid log records: 0")
    error_count_var.set("Errors and critical events: 0")
    malformed_count_var.set("Malformed lines: 0")


# --------------------------------------------------
# Function 7: Clear everything
# --------------------------------------------------

def reset_application():
    global selected_file, log_counts, detected_errors

    selected_file = ""
    log_counts = Counter()
    detected_errors = []

    file_path_var.set("")
    clear_results()


# --------------------------------------------------
# Create the main window
# --------------------------------------------------


# Create the main window
root = tk.Tk()
root.title("Log File Analyzer")
root.geometry("900x680")
root.minsize(800, 600)

# Main Application Heading
title_label = ttk.Label(
    root,
    text="Log File Analyzer",
    font=("Arial", 22, "bold")
)
title_label.pack(pady=(15, 5))

# Student Details
student_details = ttk.Label(
    root,
    text="Name: P Madhan Mohan Reddy   |   Enrollment No: 92500115162   |   Branch: CSE-AI&DS (PBL)",
    font=("Arial", 10, "bold"),
    foreground="#1f4e79"
)
student_details.pack(pady=(0, 8))




# --------------------------------------------------
# Tkinter variables
# --------------------------------------------------

file_path_var = tk.StringVar()
total_records_var = tk.StringVar(
    value="Total valid log records: 0"
)
error_count_var = tk.StringVar(
    value="Errors and critical events: 0"
)
malformed_count_var = tk.StringVar(
    value="Malformed lines: 0"
)


# --------------------------------------------------
# Application title
# --------------------------------------------------

title_label = ttk.Label(
    root,
    text="Log File Analyzer",
    font=("Arial", 22, "bold")
)
title_label.pack(pady=(15, 5))

subtitle_label = ttk.Label(
    root,
    text="Python Logging and CSV Based Application",
    font=("Arial", 11)
)
subtitle_label.pack(pady=(0, 15))


# --------------------------------------------------
# File-selection section
# --------------------------------------------------

file_frame = ttk.LabelFrame(
    root,
    text="Log File Selection",
    padding=12
)
file_frame.pack(
    fill="x",
    padx=20,
    pady=5
)

file_entry = ttk.Entry(
    file_frame,
    textvariable=file_path_var
)
file_entry.grid(
    row=0,
    column=0,
    sticky="ew",
    padx=(0, 8)
)

browse_button = ttk.Button(
    file_frame,
    text="Browse",
    command=browse_log_file
)
browse_button.grid(
    row=0,
    column=1,
    padx=4
)

generate_button = ttk.Button(
    file_frame,
    text="Generate Sample Log",
    command=generate_sample_log
)
generate_button.grid(
    row=0,
    column=2,
    padx=4
)

analyse_button = ttk.Button(
    file_frame,
    text="Analyse Log",
    command=analyse_log_file
)
analyse_button.grid(
    row=0,
    column=3,
    padx=4
)

file_frame.columnconfigure(0, weight=1)


# --------------------------------------------------
# Summary section
# --------------------------------------------------

summary_frame = ttk.LabelFrame(
    root,
    text="Log Summary",
    padding=12
)
summary_frame.pack(
    fill="x",
    padx=20,
    pady=10
)

columns = ("level", "count")

count_table = ttk.Treeview(
    summary_frame,
    columns=columns,
    show="headings",
    height=5
)

count_table.heading(
    "level",
    text="Log Level"
)

count_table.heading(
    "count",
    text="Number of Records"
)

count_table.column(
    "level",
    width=200,
    anchor="center"
)

count_table.column(
    "count",
    width=200,
    anchor="center"
)

count_table.tag_configure(
    "DEBUG",
    background="#e8e8e8"
)

count_table.tag_configure(
    "INFO",
    background="#dff2ff"
)

count_table.tag_configure(
    "WARNING",
    background="#fff3cd"
)

count_table.tag_configure(
    "ERROR",
    background="#f8d7da"
)

count_table.tag_configure(
    "CRITICAL",
    background="#e2c4ff"
)

count_table.pack(fill="x")


# --------------------------------------------------
# Statistical labels
# --------------------------------------------------

statistics_frame = ttk.Frame(root)
statistics_frame.pack(
    fill="x",
    padx=25,
    pady=5
)

ttk.Label(
    statistics_frame,
    textvariable=total_records_var,
    font=("Arial", 10, "bold")
).pack(side="left", padx=10)

ttk.Label(
    statistics_frame,
    textvariable=error_count_var,
    font=("Arial", 10, "bold")
).pack(side="left", padx=10)

ttk.Label(
    statistics_frame,
    textvariable=malformed_count_var,
    font=("Arial", 10, "bold")
).pack(side="left", padx=10)


# --------------------------------------------------
# Error-details section
# --------------------------------------------------

error_frame = ttk.LabelFrame(
    root,
    text="Detected Errors and Critical Events",
    padding=10
)
error_frame.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=10
)

error_text = tk.Text(
    error_frame,
    wrap="word",
    height=12,
    font=("Consolas", 10),
    state="disabled"
)

error_scrollbar = ttk.Scrollbar(
    error_frame,
    orient="vertical",
    command=error_text.yview
)

error_text.configure(
    yscrollcommand=error_scrollbar.set
)

error_text.pack(
    side="left",
    fill="both",
    expand=True
)

error_scrollbar.pack(
    side="right",
    fill="y"
)


# --------------------------------------------------
# Bottom buttons
# --------------------------------------------------

button_frame = ttk.Frame(root)
button_frame.pack(pady=(0, 15))

export_button = ttk.Button(
    button_frame,
    text="Export Summary to CSV",
    command=export_summary
)
export_button.grid(
    row=0,
    column=0,
    padx=5
)

reset_button = ttk.Button(
    button_frame,
    text="Reset",
    command=reset_application
)
reset_button.grid(
    row=0,
    column=1,
    padx=5
)

exit_button = ttk.Button(
    button_frame,
    text="Exit",
    command=root.destroy
)
exit_button.grid(
    row=0,
    column=2,
    padx=5
)


# Start the graphical application
root.mainloop()