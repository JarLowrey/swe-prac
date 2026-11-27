// checker.py in JavaScript, for Java and C++ solutions (the app checks their answers in the
// browser, in static/judge.js). Keep the two in step.
function check(args, expect, actual) {
  const [s] = args;
  if (typeof actual !== "string") return `Return a string, not ${actual === null ? "null" : typeof actual}.`;
  if (!s.includes(actual)) return `${JSON.stringify(actual)} is not a substring of s.`;
  if ([...actual].reverse().join("") !== actual) return `${JSON.stringify(actual)} is not a palindrome.`;
  if (actual.length < expect.length) {
    return `${JSON.stringify(actual)} has length ${actual.length}, but s has a palindrome of length ${expect.length}, such as ${JSON.stringify(expect)}.`;
  }
  return actual.length === expect.length;
}
