"""
Content for the Animation Mode 'video library'. Each lesson is a short,
self-contained animated walkthrough of one topic, built from a small set of
generic step 'kinds' that animation_lesson.html knows how to render:

  intro    — big icon + a few captions that cycle like a title card
  code     — a typed-out code snippet, optionally followed by its output
  diagram  — a small row of labeled boxes joined by arrows
  list     — a caption + a list of key points that reveal one at a time
  try      — a closing call-to-action that opens the Coding Playground
             pre-loaded with example code for this topic

These are original written explanations (not sourced from any external
course), in English only — unlike the legacy 'Getting Started' lesson,
which keeps its existing 5-language translations untouched.
"""

LESSONS = [
    dict(
        slug="python-syntax", topic_slug="python-syntax", icon="🐍",
        title="Python Syntax", color1="#22c55e", color2="#0ea5e9",
        blurb="Comments, print(), and why indentation matters.",
        steps=[
            dict(kind="intro", icon="🐍", caption="Every language has grammar rules — Python's are unusually simple.",
                 cycle=["No semicolons needed.", "No curly braces needed.", "Indentation IS the grammar."]),
            dict(kind="code", caption="A comment explains code to humans — Python ignores it completely.",
                 code="# This line prints a greeting\nprint(\"Hello, Algoria!\")",
                 output="Hello, Algoria!"),
            dict(kind="list", intro="Three syntax habits to lock in early:", items=[
                "Comments start with # and run to the end of the line.",
                "Indentation (spaces) marks which lines belong to a block — get it wrong and Python won't run.",
                "print() is how your program talks back to you.",
            ]),
            dict(kind="try", caption="Try writing your own comment and print statement.",
                 starter_code="# Write a comment here\nprint(\"Your message here\")"),
        ],
    ),
    dict(
        slug="variables", topic_slug="variables", icon="🧮",
        title="Variables", color1="#6366f1", color2="#38bdf8",
        blurb="Storing values and giving them names.",
        steps=[
            dict(kind="intro", icon="🧮", caption="A variable is a labeled box that holds a value.",
                 cycle=["Give it a name.", "Give it a value.", "Use the name whenever you need the value."]),
            dict(kind="code", caption="Assignment (=) stores a value in a name — it doesn't compare anything.",
                 code="score = 10\nscore = score + 5\nprint(score)",
                 output="15"),
            dict(kind="list", intro="What's actually happening:", items=[
                "score = 10 creates the variable and stores 10 in it.",
                "score = score + 5 reads the old value, adds 5, and stores the new value back.",
                "A variable can be reassigned as many times as you like — it just remembers the latest value.",
            ]),
            dict(kind="try", caption="Try changing a variable's value a few times.",
                 starter_code="score = 10\nscore = score + 5\nprint(score)"),
        ],
    ),
    dict(
        slug="operators", topic_slug="operators", icon="➕",
        title="Operators", color1="#f97316", color2="#ef4444",
        blurb="Arithmetic, comparison, and logical operators.",
        steps=[
            dict(kind="intro", icon="➕", caption="Operators are the small symbols that do the actual work.",
                 cycle=["+ - * / for arithmetic.", "== != < > for comparison.", "and / or / not for logic."]),
            dict(kind="code", caption="// and % are the two operators beginners forget most often.",
                 code="print(10 // 3)   # floor division\nprint(10 % 3)    # remainder",
                 output="3\n1"),
            dict(kind="list", intro="Good to remember:", items=[
                "== checks equality; a single = assigns a value — mixing them up is a classic bug.",
                "// divides and drops the decimal part; % gives you just the remainder.",
                "and/or/not combine True/False conditions, and are usually paired with if statements.",
            ]),
            dict(kind="try", caption="Try a few operators on your own numbers.",
                 starter_code="a = 17\nb = 5\nprint(a // b, a % b, a > b)"),
        ],
    ),
    dict(
        slug="data-types", topic_slug="data-types", icon="🔤",
        title="Data Types", color1="#a855f7", color2="#ec4899",
        blurb="int, float, str, bool — and converting between them.",
        steps=[
            dict(kind="intro", icon="🔤", caption="Every value in Python has a type, and the type decides what you can do with it.",
                 cycle=["Numbers: int, float.", "Text: str.", "Yes/no: bool."]),
            dict(kind="code", caption="type() tells you what kind of value you're holding.",
                 code="print(type(7))\nprint(type(7.0))\nprint(type(\"7\"))",
                 output="<class 'int'>\n<class 'float'>\n<class 'str'>"),
            dict(kind="list", intro="Key distinctions:", items=[
                "7 (int) and 7.0 (float) are both numbers, but float allows decimals.",
                "\"7\" is text (str) — Python won't do math with it until you convert it.",
                "int(), float() and str() convert a value from one type to another.",
            ]),
            dict(kind="try", caption="Try converting input() text into a number.",
                 starter_code="age_text = \"16\"\nage = int(age_text)\nprint(age + 1)"),
        ],
    ),
    dict(
        slug="input-output", topic_slug="input-output", icon="💬",
        title="Input & Output", color1="#14b8a6", color2="#6366f1",
        blurb="Getting text from the user and showing results back.",
        steps=[
            dict(kind="intro", icon="💬", caption="A program that can't talk to its user isn't very useful.",
                 cycle=["input() listens.", "print() speaks.", "Together they make a conversation."]),
            dict(kind="diagram", caption="Every interactive program follows the same shape:",
                 boxes=[{"label": "Input", "variant": "plain"}, {"label": "Process", "variant": "accent"},
                        {"label": "Output", "variant": "plain"}]),
            dict(kind="code", caption="input() always returns text — even if it looks like a number.",
                 code="name = input(\"What's your name? \")\nprint(\"Hi, \" + name + \"!\")",
                 output="What's your name? Alex\nHi, Alex!"),
            dict(kind="try", caption="Try asking for the user's name and greeting them.",
                 starter_code="name = input(\"What's your name? \")\nprint(\"Hi, \" + name + \"!\")"),
        ],
    ),
    dict(
        slug="conditions", topic_slug="conditions", icon="🔀",
        title="Conditions", color1="#f59e0b", color2="#dc2626",
        blurb="Making decisions with if / elif / else.",
        steps=[
            dict(kind="intro", icon="🔀", caption="Conditions let your program choose what to do next.",
                 cycle=["Check something.", "True → do this.", "False → do that instead."]),
            dict(kind="diagram", caption="An if / elif / else is really just a fork in the road:",
                 boxes=[{"label": "score >= 90 ?", "variant": "accent"}, {"label": "\"A\"", "variant": "plain"},
                        {"label": "else: \"B\"", "variant": "plain"}]),
            dict(kind="code", caption="Only the FIRST matching branch runs — the rest are skipped.",
                 code="score = 72\nif score >= 90:\n    print(\"A\")\nelif score >= 70:\n    print(\"B\")\nelse:\n    print(\"C\")",
                 output="B"),
            dict(kind="try", caption="Try changing the score and see which branch runs.",
                 starter_code="score = 72\nif score >= 90:\n    print(\"A\")\nelif score >= 70:\n    print(\"B\")\nelse:\n    print(\"C\")"),
        ],
    ),
    dict(
        slug="loops", topic_slug="loops", icon="🔁",
        title="Loops", color1="#0ea5e9", color2="#22c55e",
        blurb="Repeating work with for and while.",
        steps=[
            dict(kind="intro", icon="🔁", caption="A loop lets you say 'do this many times' instead of copy-pasting code.",
                 cycle=["for — repeat a known number of times.", "while — repeat until a condition changes.",
                        "break stops a loop early."]),
            dict(kind="code", caption="range(5) produces 0,1,2,3,4 — five values, so the loop runs 5 times.",
                 code="total = 0\nfor n in range(5):\n    total += n\nprint(total)",
                 output="10"),
            dict(kind="list", intro="for vs while, in one line each:", items=[
                "Use for when you know how many times (a list, or range(n)).",
                "Use while when you're repeating until something becomes True/False.",
                "break exits the loop immediately; continue skips to the next round.",
            ]),
            dict(kind="try", caption="Try writing your own for loop.",
                 starter_code="for n in range(5):\n    print(n, \"squared is\", n * n)"),
        ],
    ),
    dict(
        slug="functions", topic_slug="functions", icon="🧩",
        title="Functions", color1="#8b5cf6", color2="#3b82f6",
        blurb="Packaging code into reusable, named pieces.",
        steps=[
            dict(kind="intro", icon="🧩", caption="A function is a mini-program with a name — write it once, use it anywhere.",
                 cycle=["def names it.", "() takes inputs.", "return sends a result back."]),
            dict(kind="diagram", caption="Calling a function is a round trip:",
                 boxes=[{"label": "inputs", "variant": "plain"}, {"label": "add(a, b)", "variant": "accent"},
                        {"label": "return value", "variant": "plain"}]),
            dict(kind="code", caption="Without a return statement, a function silently gives back None.",
                 code="def add(a, b):\n    return a + b\n\nprint(add(2, 3))",
                 output="5"),
            dict(kind="try", caption="Try writing your own small function.",
                 starter_code="def add(a, b):\n    return a + b\n\nprint(add(4, 7))"),
        ],
    ),
    dict(
        slug="modular-design", topic_slug="modular-design", icon="🏗️",
        title="Modular Program Design", color1="#0891b2", color2="#7c3aed",
        blurb="Splitting a program into small, organized pieces.",
        steps=[
            dict(kind="intro", icon="🏗️", caption="Big programs get unmanageable fast — unless you break them into small pieces.",
                 cycle=["One function, one job.", "Small pieces are easy to test.", "Reuse instead of repeat."]),
            dict(kind="diagram", caption="One task, split into focused functions:",
                 boxes=[{"label": "get_input()", "variant": "plain"}, {"label": "calculate()", "variant": "accent"},
                        {"label": "show_result()", "variant": "plain"}]),
            dict(kind="list", intro="Why bother splitting things up?", items=[
                "Each function does one clear job, so bugs are easier to find.",
                "You can reuse a function in more than one place without retyping it.",
                "Other people (and future you) can read a well-named function without reading its insides.",
            ]),
            dict(kind="try", caption="Try splitting a task across two small functions.",
                 starter_code="def get_price():\n    return 250\n\ndef add_tax(price):\n    return price * 1.18\n\nprint(add_tax(get_price()))"),
        ],
    ),
    dict(
        slug="lists", topic_slug="lists", icon="📋",
        title="Lists", color1="#22c55e", color2="#0ea5e9",
        blurb="Ordered, changeable collections of values.",
        steps=[
            dict(kind="intro", icon="📋", caption="A list holds many values in one variable, in order.",
                 cycle=["Indexed from 0.", "Can grow and shrink.", "Can hold anything — even other lists."]),
            dict(kind="code", caption="append() adds to the end; indexing starts counting from 0.",
                 code="fruits = [\"apple\", \"banana\"]\nfruits.append(\"cherry\")\nprint(fruits[0], fruits[-1])",
                 output="apple cherry"),
            dict(kind="list", intro="Things worth knowing:", items=[
                "fruits[0] is the first item; fruits[-1] is the last — negative indexes count from the end.",
                "Lists are mutable: you can change, add, or remove items after creating them.",
                "len(fruits) tells you how many items are inside.",
            ]),
            dict(kind="try", caption="Try building and indexing your own list.",
                 starter_code="fruits = [\"apple\", \"banana\", \"cherry\"]\nfruits.append(\"mango\")\nprint(fruits)"),
        ],
    ),
    dict(
        slug="tuples", topic_slug="tuples", icon="📦",
        title="Tuples", color1="#f97316", color2="#a855f7",
        blurb="Like lists, but locked once created.",
        steps=[
            dict(kind="intro", icon="📦", caption="A tuple is a list's stricter sibling: once made, it can't be changed.",
                 cycle=["Written with ( ).", "Immutable — no adding or removing.", "Great for fixed groups of values."]),
            dict(kind="code", caption="Unpacking lets you assign a tuple's values to variables in one line.",
                 code="point = (3, 7)\nx, y = point\nprint(x, y)",
                 output="3 7"),
            dict(kind="list", intro="List vs tuple, quickly:", items=[
                "Lists use [ ]; tuples use ( ).",
                "Lists can change after creation (mutable); tuples cannot (immutable).",
                "Use a tuple when the values shouldn't accidentally change, like a coordinate pair.",
            ]),
            dict(kind="try", caption="Try unpacking a tuple of your own.",
                 starter_code="point = (10, 20)\nx, y = point\nprint(\"x is\", x, \"y is\", y)"),
        ],
    ),
    dict(
        slug="sets", topic_slug="sets", icon="🔗",
        title="Sets", color1="#3b82f6", color2="#14b8a6",
        blurb="Unordered collections with no duplicates.",
        steps=[
            dict(kind="intro", icon="🔗", caption="A set automatically throws away duplicates and doesn't keep order.",
                 cycle=["No duplicates allowed.", "No guaranteed order.", "Great for membership checks."]),
            dict(kind="code", caption="Notice the duplicate 2 disappears automatically.",
                 code="nums = {1, 2, 2, 3}\nprint(nums)\nprint(3 in nums)",
                 output="{1, 2, 3}\nTrue"),
            dict(kind="list", intro="When to reach for a set:", items=[
                "You need to remove duplicates from a collection of values.",
                "You need a fast 'is this value in here?' check with in.",
                "You don't care about the order of the items — only which ones exist.",
            ]),
            dict(kind="try", caption="Try removing duplicates from your own list.",
                 starter_code="nums = [1, 2, 2, 3, 3, 3]\nunique = set(nums)\nprint(unique)"),
        ],
    ),
    dict(
        slug="dictionaries", topic_slug="dictionaries", icon="📖",
        title="Dictionaries", color1="#ec4899", color2="#6366f1",
        blurb="Key-value pairs for looking things up by name.",
        steps=[
            dict(kind="intro", icon="📖", caption="A dictionary looks things up by a key, not by position.",
                 cycle=["key: value pairs.", "Look up by name, not by index.", "Like a real dictionary — word, then meaning."]),
            dict(kind="code", caption="get() is a safe lookup — no crash if the key is missing.",
                 code="student = {\"name\": \"Alex\", \"age\": 16}\nprint(student[\"name\"])\nprint(student.get(\"grade\", \"n/a\"))",
                 output="Alex\nn/a"),
            dict(kind="list", intro="Good habits with dictionaries:", items=[
                "student[\"name\"] looks up the value stored under the key \"name\".",
                "student.get(\"grade\", \"n/a\") returns \"n/a\" instead of crashing if \"grade\" doesn't exist.",
                "student[\"grade\"] = \"10th\" adds a brand-new key-value pair.",
            ]),
            dict(kind="try", caption="Try building your own dictionary.",
                 starter_code="student = {\"name\": \"Alex\", \"age\": 16}\nstudent[\"grade\"] = \"10th\"\nprint(student)"),
        ],
    ),
    dict(
        slug="strings", topic_slug="strings", icon="🔡",
        title="Strings & Data Handling", color1="#6366f1", color2="#22c55e",
        blurb="Slicing, joining and cleaning up text.",
        steps=[
            dict(kind="intro", icon="🔡", caption="Text in Python is a string — and it behaves a lot like a list of characters.",
                 cycle=["Indexed like a list.", "Sliceable with [start:end].", "Comes with dozens of built-in methods."]),
            dict(kind="code", caption="split() breaks text apart wherever the separator appears.",
                 code="data = \"3,7,9\"\nvalues = data.split(\",\")\nprint(values)\nprint(len(values))",
                 output="['3', '7', '9']\n3"),
            dict(kind="list", intro="Handy string moves:", items=[
                "text[1:4] slices out characters at index 1, 2, 3 (the end index is excluded).",
                "\"hi\".upper() and \"HI\".lower() change case without modifying the original string.",
                "\" \".join([...]) is the reverse of split() — it stitches a list back into one string.",
            ]),
            dict(kind="try", caption="Try slicing and splitting a string of your own.",
                 starter_code="sentence = \"the cat sat on the mat\"\nwords = sentence.split()\nprint(words[0], words[-1])"),
        ],
    ),
]


def get_lesson(slug):
    for lesson in LESSONS:
        if lesson["slug"] == slug:
            return lesson
    return None
