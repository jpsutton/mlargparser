MLArgParser
===========
MLArgParser is a Multi-Level Argument Parser library for writing CLI-based applications.  Object-oriented Programming concepts such as instance methods, sub-classes, and method arguments are mapped directly to CLI commands, sub-commands, and command arguments respectively.

Additionally, Python docstrings on methods/classes, default values on method parameters, and a simple dictionary are used to automatically build help output, which is formatted in a standard way.  Finally, type-hinting (PEP-484) is utilized to allow the library to automatically convert user-provided CLI parameters to the correct data-types expected by your code; most every-day Python data types (strings, integers, booleans, lists, dictionaries, and sets) are all supported as CLI-provided parameters.

The over-arching idea here is that app developers don't like spending lots of time building user-facing documentation (like help output) or building the code necessary to properly parse input data. In fact, parsing CLI input tends to be rather tedious and error-proned. This library is intended to allow the developer to take a break from having to deal with parsing and documentation details, and does so by forcing the developer to write code which is easier to understand (self-documenting) and structured in a way which closely matches the way the user interacts with the application.


Example
=======
```python
#!/usr/bin/env python3

from mlargparser import MLArgParser

class MyApp (MLArgParser):
  """ My Amazing App """
  
  argDesc = {
    'arg1': 'arg1 description here',
    'arg2': 'arg2 description here',
    'arg3': 'arg3 description here',
  }

  def command1 (self, arg1: int, arg2: str, arg3: str = "default value"):
    """ command1 description here """
    if arg1 == 0:
      print("arg2 = %s" % arg2)
      print("arg3 = %s" % arg3)

if __name__ == '__main__':
  MyApp()
```

The above minimal example creates an application which has one possible command named "command1" which takes 2 required parameters of "arg1" (integer) and "arg2" (string), and an additional optional parameter of "arg3" (string).  
If the user passes zero for arg1, then the values for arg2 and arg3 are both printed back to the user.  If you were to call the application with only --help or -h, the output would be as follows:

```
[user@localhost]: ~>$ ./myprog.py --help
usage: ./myprog.py <command> [<args>]

My Amazing App

positional arguments:
  command     Sub-command to run

optional arguments:
  -h, --help  show this help message and exit

available commands:
  command1      command1 description here
```

If you get more specific and provide the required "command" positional parameter followed by --help or -h, the output would be as follows:

```
[user@localhost]: ~>$ ./myprog.py command1 --help
usage: ./myprog.py command1 [<args>]

command1 description here

optional arguments:
  -h, --help            show this help message and exit
  --arg3 ARG3           arg3 description here

required arguments:
  --arg1 ARG1, -a ARG1  arg1 description here
  --arg2 ARG2           arg2 description here

```

Calling the application with the correct parameters is as you would expect:

```
[user@localhost]: ~>$ ./myprog.py command1 --arg1 0 --arg2 testing123
arg2 = testing123
arg3 = default value
```


Licensing
=========
Unless otherwise noted, all the code in this repository is licensed under the GNU General Public License, Version 2 (GPLv2) ONLY.  If you find yourself in the extraordinarily 
unusual situation of needing to use my code under a more permissive license, send me an email, and we'll see if we can work something out.  I'm a pretty nice guy, so don't be 
afraid to speak up (so long as you're polite).
