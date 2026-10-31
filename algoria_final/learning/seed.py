"""
Sample content so Algoria works immediately after installation:
topics + a question bank covering all four learning modules (Python
Fundamentals, Control Flow & Functions, Data Structures, File & Exception
Handling), plus a few "Build Something Real" project briefs.

`ensure_seeded()` is cheap to call on every request that needs this data —
it does nothing once the tables are already populated.
"""

TOPICS = [
    # slug, name, group, order, icon
    ("python-syntax", "Python Syntax", "foundations", 1, "🐍"),
    ("variables", "Variables", "foundations", 2, "🧮"),
    ("operators", "Operators", "foundations", 3, "➕"),
    ("data-types", "Data Types", "foundations", 4, "🔤"),
    ("input-output", "Input & Output", "foundations", 5, "💬"),

    ("conditions", "Conditions", "control_flow", 1, "🔀"),
    ("loops", "Loops", "control_flow", 2, "🔁"),
    ("functions", "Functions", "control_flow", 3, "🧩"),
    ("modular-design", "Modular Program Design", "control_flow", 4, "🏗️"),

    ("lists", "Lists", "data_structures", 1, "📋"),
    ("tuples", "Tuples", "data_structures", 2, "📦"),
    ("sets", "Sets", "data_structures", 3, "🔗"),
    ("dictionaries", "Dictionaries", "data_structures", 4, "📖"),
    ("strings", "Strings & Data Handling", "data_structures", 5, "🔡"),

    ("file-handling", "File Handling", "file_handling", 1, "📁"),
    ("exception-handling", "Exception Handling", "file_handling", 2, "🚫"),
]

# (topic_slug, difficulty, text, opt1, opt2, opt3, opt4, correct(1-4), explanation)
QUESTIONS = [
    ("python-syntax", "easy", "Which symbol starts a comment in Python?",
     "#", "//", "/* */", "<!-- -->", 1, "Python comments start with a `#` and run to the end of the line."),
    ("python-syntax", "easy", "What does `print('Hello')` output?",
     "Hello", "'Hello'", "an error", "nothing", 1, "`print()` displays the text without the surrounding quotes."),
    ("python-syntax", "medium", "Which of these is a valid Python variable name?",
     "2var", "_var", "var-name", "var name", 2, "Names can start with a letter or underscore, but not a digit, hyphen or space."),
    ("python-syntax", "hard", "How do you continue a long statement onto the next line?",
     "a backslash \\ at the end of the line", "a semicolon ;", "a comma ,", "a colon :", 1, "A trailing backslash tells Python the logical line continues below."),

    ("variables", "easy", "What is the output?\nx = 5\nprint(x)",
     "5", "'5'", "x", "Error", 1, "`x` stores the integer 5, so printing it shows 5."),
    ("variables", "easy", "Which line correctly assigns 10 to a variable y?",
     "y = 10", "10 = y", "var y = 10", "int y = 10", 1, "Python assignment is `name = value` — no type keyword needed."),
    ("variables", "medium", "What happens here?\nx = 5\nx = 'hello'\nprint(x)",
     "It prints hello — Python variables can be reassigned to a new type", "It raises an error", "It prints 5", "It prints hello5", 1, "Python is dynamically typed: a variable can be rebound to a value of any type."),
    ("variables", "hard", "What is b after this runs?\na = 3\nb = a\na = 7",
     "b is 3", "b is 7", "b is undefined", "Error", 1, "`b = a` copies the value 3. Later changing `a` doesn't affect `b`."),

    ("operators", "easy", "What is the result of `7 // 2`?",
     "3", "3.5", "4", "1", 1, "`//` is floor division — it divides and rounds down to the nearest whole number."),
    ("operators", "easy", "What does the `%` operator do?",
     "Gives the remainder of a division", "Converts to a percentage", "Multiplies two numbers", "Divides two numbers", 1, "`%` is the modulo operator — it returns what's left over after division."),
    ("operators", "medium", "What is the output of `2 ** 3`?",
     "8", "6", "9", "5", 1, "`**` is exponentiation: 2 to the power of 3 is 8."),
    ("operators", "hard", "What is the result of `5 == '5'`?",
     "False", "True", "Error", "None", 1, "An int and a str are never equal in Python, even if they 'look' the same."),

    ("data-types", "easy", "What is the data type of `x = 3.14`?",
     "float", "int", "str", "bool", 1, "Numbers with a decimal point are `float` in Python."),
    ("data-types", "easy", "What does `type('hello')` return?",
     "<class 'str'>", "<class 'int'>", "<class 'list'>", "<class 'char'>", 1, "Text in quotes is a string, Python's `str` type."),
    ("data-types", "medium", "Which of these data types is immutable?",
     "tuple", "list", "dict", "set", 1, "Tuples can't be changed after creation; lists, dicts and sets can."),
    ("data-types", "hard", "What does `type(True)` return?",
     "<class 'bool'>", "<class 'int'>", "<class 'str'>", "<class 'NoneType'>", 1, "`True`/`False` are the `bool` type (a subtype of int, but their own type)."),

    ("input-output", "easy", "Which function reads text typed by the user?",
     "input()", "read()", "get()", "scan()", 1, "`input()` pauses the program and returns what the user types."),
    ("input-output", "easy", "What type does `input()` always return?",
     "str", "int", "float", "bool", 1, "Everything typed by the user comes back as text (`str`) — convert it yourself if you need a number."),
    ("input-output", "medium", "How do you print two values separated by a space?",
     "print(a, b)", "print(a+b)", "print(a b)", "print(a; b)", 1, "`print()` joins comma-separated arguments with a single space by default."),
    ("input-output", "hard", "What happens with `int(input())` if the user types 'abc'?",
     "It raises a ValueError", "It returns 0", "It returns None", "It returns 'abc'", 1, "`int()` can't convert non-numeric text, so it raises a ValueError."),

    ("conditions", "easy", "Which keyword starts a conditional check?",
     "if", "when", "then", "check", 1, "`if` is Python's keyword for conditional branching."),
    ("conditions", "easy", "What does this print?\nx = 10\nif x > 5:\n    print('big')",
     "big", "nothing", "Error", "10", 1, "Since 10 > 5 is True, the indented `print('big')` runs."),
    ("conditions", "medium", "Which keyword means 'else, if this other thing is true'?",
     "elif", "elseif", "else if", "elsif", 1, "Python spells this `elif`, not `else if`."),
    ("conditions", "hard", "What does `if not x:` do when `x = []`?",
     "The block runs — an empty list is 'falsy'", "The block is skipped", "It raises an error", "It always runs regardless of x", 1, "Empty containers like `[]` count as False, so `not x` is True."),

    ("loops", "easy", "Which loop runs a fixed number of times using range()?",
     "for", "while", "do-while", "repeat", 1, "`for i in range(n):` is Python's standard counted loop."),
    ("loops", "easy", "What does `break` do inside a loop?",
     "Exits the loop immediately", "Skips just this one iteration", "Restarts the loop", "Does nothing", 1, "`break` stops the loop entirely, even if there were more iterations left."),
    ("loops", "medium", "How many times does `for i in range(5):` run?",
     "5", "4", "6", "It runs forever", 1, "`range(5)` produces 0,1,2,3,4 — five values."),
    ("loops", "hard", "What does `continue` do inside a loop?",
     "Skips the rest of the current iteration and moves to the next one", "Exits the loop", "Pauses the loop", "Restarts the whole program", 1, "`continue` jumps straight to the next iteration, skipping any code after it in that pass."),

    ("functions", "easy", "Which keyword defines a function?",
     "def", "function", "func", "define", 1, "Functions start with `def name(...):`."),
    ("functions", "easy", "What does `return` do in a function?",
     "Sends a value back to whoever called the function", "Prints a value to the screen", "Ends the whole program", "Repeats the function", 1, "`return` hands a result back to the caller; it doesn't print anything by itself."),
    ("functions", "medium", "What does this print?\ndef add(a, b):\n    return a + b\nprint(add(2, 3))",
     "5", "23", "Error", "None", 1, "`add(2, 3)` returns 2 + 3 = 5."),
    ("functions", "hard", "What does a function return if it has no `return` statement?",
     "None", "It raises an error", "0", "An empty string", 1, "A function with no explicit `return` implicitly returns `None`."),

    ("modular-design", "easy", "What is the main benefit of splitting a program into functions?",
     "Code becomes reusable and easier to organize", "The program always runs faster", "The file always becomes smaller", "There is no real benefit", 1, "Breaking logic into functions makes it reusable, testable and easier to read."),
    ("modular-design", "easy", "Which keyword lets you use code from another file?",
     "import", "include", "require", "using", 1, "`import module_name` brings in code defined elsewhere."),
    ("modular-design", "medium", "What is a 'module' in Python?",
     "A file containing Python code you can reuse elsewhere", "A type of loop", "A built-in data type", "An error message", 1, "Any `.py` file can be imported as a module."),
    ("modular-design", "hard", "Why is modular design considered good practice?",
     "It makes code easier to test, reuse and maintain", "It removes the need for variables entirely", "It guarantees the program has no bugs", "It prevents the program from using functions", 1, "Smaller, focused pieces are easier to understand, test and fix independently."),

    ("lists", "easy", "How do you create an empty list?",
     "[]", "()", "{}", "<>", 1, "Square brackets `[]` create a list — empty or with items."),
    ("lists", "easy", "What does this print?\nnums = [1, 2, 3]\nprint(nums[0])",
     "1", "2", "3", "Error", 1, "List indexing starts at 0, so `nums[0]` is the first item, 1."),
    ("lists", "medium", "Which method adds an item to the end of a list?",
     "append()", "add()", "insert()", "push()", 1, "`list.append(item)` adds one item to the end."),
    ("lists", "hard", "What does this print?\na = [1, 2, 3]\nb = a\nb.append(4)\nprint(a)",
     "[1, 2, 3, 4]", "[1, 2, 3]", "Error", "[4]", 1, "`b = a` doesn't copy the list — both names point to the same list, so changing `b` changes `a` too."),

    ("tuples", "easy", "How are tuples different from lists?",
     "Tuples are immutable; lists can be changed", "Tuples can only hold numbers", "Lists can't hold strings", "There is no difference", 1, "Once created, a tuple's contents can't be changed — unlike a list."),
    ("tuples", "easy", "How do you write a tuple with exactly one item?",
     "(5,) — with a trailing comma", "(5)", "[5]", "{5}", 1, "Without the trailing comma, `(5)` is just the number 5 in parentheses."),
    ("tuples", "medium", "What does this print?\nt = (1, 2, 3)\nprint(t[1])",
     "2", "1", "3", "Error", 1, "Tuples are indexed the same way as lists — `t[1]` is the second item, 2."),
    ("tuples", "hard", "What happens if you try `t[0] = 99` on a tuple `t`?",
     "A TypeError — tuples can't be modified", "It works fine and changes the value", "It returns None", "It silently deletes the tuple", 1, "Tuples are immutable, so item assignment raises a TypeError."),

    ("sets", "easy", "What is a key feature of a Python set?",
     "It stores unique, unordered items", "It stores ordered items with duplicates allowed", "It's identical to a list", "It's identical to a dictionary", 1, "Sets automatically drop duplicates and don't keep a fixed order."),
    ("sets", "easy", "How do you create a set with the numbers 1, 2, 3?",
     "{1, 2, 3}", "[1, 2, 3]", "(1, 2, 3)", "<1, 2, 3>", 1, "Curly braces with comma-separated values create a set."),
    ("sets", "medium", "What does this print?\ns = {1, 2, 2, 3}\nprint(len(s))",
     "3", "4", "2", "1", 1, "Sets automatically remove duplicates, so `{1,2,2,3}` only keeps one 2."),
    ("sets", "hard", "Which method adds a single item to a set?",
     "add()", "append()", "insert()", "push()", 1, "Sets use `.add(item)`, not `.append()` like lists."),

    ("dictionaries", "easy", "How do you create an empty dictionary?",
     "{}", "[]", "()", "dict[]", 1, "Empty curly braces `{}` create an empty dictionary."),
    ("dictionaries", "easy", "What does this print?\nd = {'a': 1}\nprint(d['a'])",
     "1", "'a'", "Error", "None", 1, "`d['a']` looks up the value stored under the key `'a'`, which is 1."),
    ("dictionaries", "medium", "How do you add a new key-value pair to dictionary `d`?",
     "d['key'] = value", "d.add(key, value)", "d.append(key, value)", "d.push(key, value)", 1, "Assigning to a new key, like `d['key'] = value`, adds it to the dictionary."),
    ("dictionaries", "hard", "What happens when you access `d['x']` and `'x'` isn't a key in `d`?",
     "A KeyError is raised", "It returns None", "It returns 0", "It silently creates that key", 1, "Direct key access raises a KeyError if the key is missing — use `.get()` to avoid that."),

    ("strings", "easy", "How do you find the length of a string `s`?",
     "len(s)", "s.length()", "s.size()", "size(s)", 1, "`len()` works on strings (and lists, tuples, etc.) to count their items."),
    ("strings", "easy", "What does this print?\ns = 'hello'\nprint(s[0])",
     "h", "e", "hello", "Error", 1, "String indexing starts at 0, so `s[0]` is the first character, 'h'."),
    ("strings", "medium", "Which method converts a string to uppercase?",
     ".upper()", ".toUpper()", ".capitalize()", ".upperCase()", 1, "Python strings use `.upper()` (lowercase method name, no camelCase)."),
    ("strings", "hard", "What does `print('abc' + 'def')` output?",
     "abcdef", "ab cdef", "Error", "a b c d e f", 1, "The `+` operator on strings concatenates them directly, with no added space."),

    ("file-handling", "easy", "Which function opens a file in Python?",
     "open()", "file()", "read()", "load()", 1, "`open(filename, mode)` returns a file object you can read from or write to."),
    ("file-handling", "easy", "Which mode opens a file for writing, erasing any existing content?",
     "'w'", "'r'", "'a'", "'x-'", 1, "`'w'` (write) creates the file if needed and erases whatever was in it before."),
    ("file-handling", "medium", "Why is `with open('data.txt') as f:` preferred over calling `open()`/`close()` manually?",
     "It automatically closes the file, even if an error occurs", "It reads the file faster", "It's the only way to read text files", "It prevents the file from being edited later", 1, "The `with` block guarantees `f.close()` runs automatically once the block ends."),
    ("file-handling", "hard", "What does `'a'` mode do when opening a file that already has content?",
     "Adds new writes to the end, keeping existing content", "Erases the file first", "Raises an error because the file exists", "Opens it as read-only", 1, "Append mode ('a') writes new data after whatever is already in the file."),

    ("exception-handling", "easy", "Which block catches an error so the program doesn't crash?",
     "except", "catch", "rescue", "error", 1, "Python pairs `try` with `except` blocks to catch and handle errors."),
    ("exception-handling", "easy", "What error does `int('abc')` raise?",
     "ValueError", "TypeError", "KeyError", "NameError", 1, "`'abc'` can't be converted to an int, so Python raises a ValueError."),
    ("exception-handling", "medium", "What does this print?\ntry:\n    print(10 / 0)\nexcept ZeroDivisionError:\n    print('caught it')",
     "caught it", "10", "an unhandled crash", "0", 1, "Dividing by zero raises ZeroDivisionError, which the except block catches and handles."),
    ("exception-handling", "hard", "What is special about code inside a `finally:` block?",
     "It always runs, whether or not an exception occurred", "It only runs if there was no error", "It only runs if there was an error", "It never runs automatically", 1, "`finally` runs unconditionally — it's the right place for cleanup that must always happen."),
]

PROJECTS = [
    dict(
        slug="calculator", order=1, xp_reward=50,
        title="Simple Calculator",
        brief="Build a command-line calculator that asks the user for two numbers and an "
              "operation (+, -, *, /), then prints the result.",
        starter_code=(
            "# Simple Calculator\n"
            "a = float(input(\"Enter first number: \"))\n"
            "b = float(input(\"Enter second number: \"))\n"
            "op = input(\"Choose an operation (+, -, *, /): \")\n"
            "\n"
            "# TODO: use if/elif to compute the result based on `op`\n"
            "# and print it.\n"
        ),
        checklist=(
            "Asks the user for two numbers\n"
            "Asks the user which operation to perform\n"
            "Uses if/elif to handle +, -, * and /\n"
            "Prints a clearly labelled result\n"
            "Handles division by zero without crashing"
        ),
    ),
    dict(
        slug="guessing-game", order=2, xp_reward=50,
        title="Number Guessing Game",
        brief="The computer picks a secret number between 1 and 100. The player keeps "
              "guessing until they get it right, and after each guess your program says "
              "'too high' or 'too low'.",
        starter_code=(
            "import random\n"
            "\n"
            "secret = random.randint(1, 100)\n"
            "guess = None\n"
            "\n"
            "# TODO: loop until the player guesses correctly.\n"
            "# Read a guess with input(), compare it to `secret`,\n"
            "# and print a hint each time.\n"
        ),
        checklist=(
            "Picks a random secret number\n"
            "Uses a loop that keeps asking until the guess is correct\n"
            "Tells the player 'too high' or 'too low' after each guess\n"
            "Congratulates the player and stops when they guess correctly\n"
            "Counts and displays how many guesses it took"
        ),
    ),
    dict(
        slug="grade-calculator", order=3, xp_reward=50,
        title="Student Grade Calculator",
        brief="Ask the user for marks in 3 subjects, calculate the average, and print a "
              "letter grade (A/B/C/F) using conditions.",
        starter_code=(
            "m1 = float(input(\"Marks in subject 1: \"))\n"
            "m2 = float(input(\"Marks in subject 2: \"))\n"
            "m3 = float(input(\"Marks in subject 3: \"))\n"
            "\n"
            "# TODO: compute the average of m1, m2, m3\n"
            "# TODO: use if/elif/else to decide a grade and print it\n"
        ),
        checklist=(
            "Reads three subject marks from the user\n"
            "Computes the average correctly\n"
            "Uses if/elif/else to assign a letter grade\n"
            "Prints both the average and the grade clearly\n"
            "Code is organized into readable steps with comments"
        ),
    ),
    dict(
        slug="student-record-logger", order=4, xp_reward=60,
        title="Student Record Logger",
        brief="Build a small tool that saves student names and marks to a text file, "
              "then reads the file back and prints a summary — using 'with open(...)' "
              "for both writing and reading.",
        starter_code=(
            "# Student Record Logger\n"
            "records = [\n"
            "    (\"Aria\", 92),\n"
            "    (\"Kabir\", 78),\n"
            "    (\"Meera\", 85),\n"
            "]\n"
            "\n"
            "# TODO: open 'students.txt' in write mode and save one\n"
            "# 'name,marks' line per record.\n"
            "\n"
            "# TODO: open 'students.txt' again in read mode, read it back\n"
            "# line by line, and print each name with their marks.\n"
            "\n"
            "# TODO: also print the class average at the end.\n"
        ),
        checklist=(
            "Writes each student's name and marks to students.txt\n"
            "Uses 'with open(...) as f:' for both writing and reading\n"
            "Reads the file back and prints every record\n"
            "Calculates and prints the class average\n"
            "Appends a new record without erasing earlier ones (bonus)"
        ),
    ),
    dict(
        slug="safe-division-calculator", order=5, xp_reward=60,
        title="Safe Division Calculator",
        brief="A calculator that keeps asking the user for two numbers and divides them — "
              "but never crashes, no matter what the user types or how many times they "
              "divide by zero.",
        starter_code=(
            "# Safe Division Calculator\n"
            "while True:\n"
            "    a = input(\"First number (or 'q' to quit): \")\n"
            "    if a.lower() == 'q':\n"
            "        break\n"
            "    b = input(\"Second number: \")\n"
            "\n"
            "    # TODO: wrap the conversion and division in try/except.\n"
            "    # Catch ValueError (bad input) and ZeroDivisionError\n"
            "    # separately, with a clear message for each, then keep looping.\n"
        ),
        checklist=(
            "Loops until the user types 'q' to quit\n"
            "Uses try/except around the conversion and division\n"
            "Handles ValueError for non-numeric input without crashing\n"
            "Handles ZeroDivisionError for a zero divisor without crashing\n"
            "Prints the result clearly whenever the division succeeds"
        ),
    ),
]


def ensure_seeded():
    from .models import Badge, Topic, Question, Project
    from . import gamification

    if not Topic.objects.exists():
        for slug, name, group, order, icon in TOPICS:
            Topic.objects.get_or_create(
                slug=slug, defaults=dict(name=name, group=group, order=order, icon=icon)
            )

    if not Question.objects.exists():
        topics_by_slug = {t.slug: t for t in Topic.objects.all()}
        for (slug, diff, text, o1, o2, o3, o4, correct, expl) in QUESTIONS:
            Question.objects.create(
                topic=topics_by_slug[slug], difficulty=diff, text=text,
                option1=o1, option2=o2, option3=o3, option4=o4,
                correct_option=correct, explanation=expl,
            )

    if not Project.objects.exists():
        for p in PROJECTS:
            Project.objects.get_or_create(slug=p["slug"], defaults=p)

    if not Badge.objects.exists():
        gamification.sync_badge_definitions()
