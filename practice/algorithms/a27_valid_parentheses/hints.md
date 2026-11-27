**Hint 1.** Counting each type isn't enough: `"([)]"` and `")("` have balanced counts but are
invalid. What must be true at the moment a closing bracket arrives?

**Hint 2.** A closing bracket must match the *most recently opened* bracket that is still open.
Which data structure gives you "the most recent unfinished thing" in O(1)?

**Hint 3.** Use a stack. Push every opening bracket. On a closing bracket, the stack must be
non-empty and its top must be the matching opener; pop it.

**Hint 4.** Two easy-to-miss cases: a closing bracket with an empty stack (`")"`), and openers
left over at the end (`"(("`). Return `not stack` rather than `True`. A dict from each closer to
its opener keeps the match to one comparison.
