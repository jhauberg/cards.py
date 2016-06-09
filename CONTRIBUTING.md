# Contributing

I appreciate any contributions, but please refer to the following sections for guidelines.

Like any true python enthusiast, I can be a bit pedantic!

## Style

 * Use spaces, not tabs
 * Strings should use single-quotes
 * Line length = 100
 * PEP8 (with exceptions)

## Commits

Keep them short and sweet.

Every commit should only deal with a single feature/bug and *must* have a message associated with it.

The message is actually more like a title and should:

 * Be properly capitalized (i.e. start with an upper-cased letter)
 * Start with something like: "Fix", "Add" or "Change"
   * ***Not***: "Fixed", "Added" or "Changed"
 * Not end with a period

If it's tough to write a good commit message, it might be a symptom of being better suited as several smaller commits.

## Make a test

**If you fix something, make sure it doesn't break something else.**

Before submitting anything, you should try running the [tests](test) (or at least the ones applicable to your fix) and ensure that everything looks right.

Each test is simply a "project" containing at least one CSV file.

You can run each test individually, or you can run them all at once by executing the [run](test/run) script.

When you run a test, make sure to use the current development module instead of the currently installed one (the [run](test/run) script does this).
