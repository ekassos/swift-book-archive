# Latest

**Latest** is a continuously updated preview of _The Swift Programming Language_ from the source repository and may include unpublished changes before an official release.

Latest commit date: Jul 30, 2026

## Upstream Commit

SHA: `67e31529a833bacadff9d4d4ad521910b9c3c0c2`

Commit message:
```text
Revert "Suppress the language version from the module name (#474)" (#475)

This reverts commit e327e452ef7c1b8e677738e7798f2a9e9925bc81, reversing
changes made to 29329996c4ec537de0b16e70609e2a6c4ecc2af7.

After getting it in place, I learned that @DisplayName() didn't have the
follow-through impact I'd presumed it did - so this is effectively a
no-op, and I didn't want to leave useless artifacts around. Turns out
that DocC only uses `@DisplayName` directive when there's an explicit
module from a surrounding package. When you're building from a "bare"
DocC catalog with a central page identified by `@TechnologyRoot`, the H1
value of that page is overrides any values.
```

- [View upstream commit](https://github.com/swiftlang/swift-book/commit/67e31529a833bacadff9d4d4ad521910b9c3c0c2)
- [Browse upstream repository](https://github.com/swiftlang/swift-book/tree/67e31529a833bacadff9d4d4ad521910b9c3c0c2)

## Pick the edition that works for you.

- [EPUB](https://raw.githubusercontent.com/ekassos/swift-book-archive/main/archive/latest/swift_book.epub)
- [Digital Light PDF](https://raw.githubusercontent.com/ekassos/swift-book-archive/main/archive/latest/swift_book_digital.pdf)
- [Digital Dark PDF](https://raw.githubusercontent.com/ekassos/swift-book-archive/main/archive/latest/swift_book_digital_dark.pdf)
- [Print Light PDF](https://raw.githubusercontent.com/ekassos/swift-book-archive/main/archive/latest/swift_book_print.pdf)
- [Print Dark PDF](https://raw.githubusercontent.com/ekassos/swift-book-archive/main/archive/latest/swift_book_print_dark.pdf)

## More

- [Back to all versions](..)
