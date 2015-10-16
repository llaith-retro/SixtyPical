SixtyPical Analysis
===================

This is a test suite, written in [Falderal][] format, for the SixtyPical
static analysis rules.

[Falderal]:     http://catseye.tc/node/Falderal

    -> Functionality "Analyze SixtyPical program" is implemented by
    -> shell command "bin/sixtypical --analyze %(test-body-file)"

    -> Tests for functionality "Analyze SixtyPical program"

### Rudiments ###

Routines must declare their inputs, outputs, and memory locations they trash.

    | routine up
    |   inputs a
    |   outputs a
    |   trashes c, z, v, n
    | {
    |     st off, c
    |     add a, 1
    | }
    = ok

Routines may not declare a memory location to be both an output and trashed.

    | routine main
    |   outputs a
    |   trashes a
    | {
    |     ld a, 0
    | }
    ? UsageClashError: a

If a routine declares it outputs a location, that location should be initialized.

    | routine main
    |   outputs a, x, z, n
    | {
    |     ld x, 0
    | }
    ? UninitializedOutputError: a

    | routine main
    |   inputs a
    |   outputs a
    | {
    | }
    = ok

If a routine declares it outputs a location, that location may or may not have
been initialized.  Trashing is mainly a signal to the caller.

    | routine main
    |   trashes x, z, n
    | {
    |     ld x, 0
    | }
    = ok

    | routine main
    |   trashes x, z, n
    | {
    | }
    = ok

If a routine modifies a location, it needs to either output it or trash it.

    | routine main
    | {
    |     ld x, 0
    | }
    ? IllegalWriteError: x

    | routine main
    |   outputs x, z, n
    | {
    |     ld x, 0
    | }
    = ok

    | routine main
    |   trashes x, z, n
    | {
    |     ld x, 0
    | }
    = ok

### ld ###

Can't `ld` from a memory location that isn't initialized.

    | routine main
    |   inputs a, x
    |   trashes a, z, n
    | {
    |     ld a, x
    | }
    = ok

    | routine main
    |   inputs a
    |   trashes a
    | {
    |     ld a, x
    | }
    ? UninitializedAccessError: x

Can't `ld` to a memory location that doesn't appear in (outputs ∪ trashes).

    | routine main
    |   trashes a, z, n
    | {
    |     ld a, 0
    | }
    = ok

    | routine main
    |   outputs a
    |   trashes z, n
    | {
    |     ld a, 0
    | }
    = ok

    | routine main
    |   outputs z, n
    |   trashes a
    | {
    |     ld a, 0
    | }
    = ok

    | routine main
    |   trashes z, n
    | {
    |     ld a, 0
    | }
    ? IllegalWriteError: a

    | routine main
    |   trashes a, n
    | {
    |     ld a, 0
    | }
    ? IllegalWriteError: z

### st ###

Can't `st` from a memory location that isn't initialized.

    | byte lives
    | routine main
    |   inputs x
    |   trashes lives
    | {
    |     st x, lives
    | }
    = ok

    | byte lives
    | routine main
    |   trashes x, lives
    | {
    |     st x, lives
    | }
    ? UninitializedAccessError: x

Can't `st` to a memory location that doesn't appear in (outputs ∪ trashes).

    | byte lives
    | routine main
    |   trashes lives
    | {
    |     st 0, lives
    | }
    = ok

    | byte lives
    | routine main
    |   outputs lives
    | {
    |     st 0, lives
    | }
    = ok

    | byte lives
    | routine main
    |   inputs lives
    | {
    |     st 0, lives
    | }
    ? IllegalWriteError: lives

### add ###

Can't `add` from or to a memory location that isn't initialized.

    | routine main
    |   inputs a
    |   outputs a
    |   trashes c, z, v, n
    | {
    |     st off, c
    |     add a, 0
    | }
    = ok

    | byte lives
    | routine main
    |   inputs a
    |   outputs a
    |   trashes c, z, v, n
    | {
    |     st off, c
    |     add a, lives
    | }
    ? UninitializedAccessError: lives

    | byte lives
    | routine main
    |   inputs lives
    |   outputs a
    |   trashes c, z, v, n
    | {
    |     st off, c
    |     add a, lives
    | }
    ? UninitializedAccessError: a

Can't `add` to a memory location that isn't writeable.

    | routine main
    |   inputs a
    |   trashes c
    | {
    |     st off, c
    |     add a, 0
    | }
    ? IllegalWriteError: a

### ... many missing tests ... ###

### call ###

When calling a routine, all of the locations it lists as inputs must be
initialized.

    | byte lives
    | 
    | routine foo
    |   inputs x
    |   trashes lives
    | {
    |     st x, lives
    | }
    | 
    | routine main
    | {
    |     call foo
    | }
    ? UninitializedAccessError: x

Note that if you call a routine that trashes a location, you also trash it.

    | byte lives
    | 
    | routine foo
    |   inputs x
    |   trashes lives
    | {
    |     st x, lives
    | }
    | 
    | routine main
    |   outputs x, z, n
    | {
    |     ld x, 0
    |     call foo
    | }
    ? IllegalWriteError: lives

    | byte lives
    | 
    | routine foo
    |   inputs x
    |   trashes lives
    | {
    |     st x, lives
    | }
    | 
    | routine main
    |   outputs x, z, n
    |   trashes lives
    | {
    |     ld x, 0
    |     call foo
    | }
    = ok

You can't output a value that the thing you called trashed.

    | byte lives
    | 
    | routine foo
    |   inputs x
    |   trashes lives
    | {
    |     st x, lives
    | }
    | 
    | routine main
    |   outputs x, z, n, lives
    | {
    |     ld x, 0
    |     call foo
    | }
    ? UninitializedOutputError: lives

...unless you write to it yourself afterwards.

    | byte lives
    | 
    | routine foo
    |   inputs x
    |   trashes lives
    | {
    |     st x, lives
    | }
    | 
    | routine main
    |   outputs x, z, n, lives
    | {
    |     ld x, 0
    |     call foo
    |     st x, lives
    | }
    = ok

If a routine declares outputs, they are initialized in the caller after
calling it.

    | routine foo
    |   outputs x, z, n
    | {
    |     ld x, 0
    | }
    | 
    | routine main
    |   outputs a
    |   trashes x, z, n
    | {
    |     call foo
    |     ld a, x
    | }
    = ok

    | routine foo
    | {
    | }
    | 
    | routine main
    |   outputs a
    |   trashes x
    | {
    |     call foo
    |     ld a, x
    | }
    ? UninitializedAccessError: x

If a routine trashes locations, they are uninitialized in the caller after
calling it.

    | routine foo
    |   trashes x, z, n
    | {
    |     ld x, 0
    | }
    = ok

    | routine foo
    |   trashes x, z, n
    | {
    |     ld x, 0
    | }
    | 
    | routine main
    |   outputs a
    |   trashes x, z, n
    | {
    |     call foo
    |     ld a, x
    | }
    ? UninitializedAccessError: x

### if ###

Both blocks of an `if` are analyzed.

    | routine foo
    |   inputs a
    |   outputs x
    |   trashes a, z, n, c
    | {
    |     cmp a, 42
    |     if z {
    |         ld x, 7
    |     } else {
    |         ld x, 23
    |     }
    | }
    = ok