# Entering grades via tables

A grade table has – in essence – rows for pupils and columns for subjects. It must also specify a context. This additional information is in special leading key-value lines:

- school year
- class
- term
- (optional) teacher

There may also be some structure and text serving documentation purposes. This can be placed in table rows with '#' in the first column.

The teacher is represented by a short tag (e.g. "AB" for Anne Brown), which should be the same as the tags used regularly in the school (assuming these exist). It allows grades to be associated with particular teachers, which can help to avoid errors. The system will only accept grades from teachers who are recorded as teaching the given subject(s) in the given class. Also, if two teachers are responsible for grading a group, an attempt by one teacher to overwrite a grade by the other will result in an error message.

There is of course the possibility for the administrator to override anyone's grades. One possibility would be a single table of all grades for a class/group. This should in any case be available as an export – as a convenient means of collecting and handling the grades. But the ability to import a complete table could also be very useful.

It might be worth considering an extension/variant which requires specification of one teacher for each grade.

An alternative way of specifying the teacher, which could be more practical if everyone is sent the same table to fill, would be to have a separate folder for each teacher (with the teacher-tag as name) and save the returned tables in the appropriate folder. 

## Checking the subjects

As the subjects available for each class are available in the CLASS_SUBJECTS table, this list could be used to ensure that all relevant subjects are present in the mapping – and that there are no unexpected ones. Individual subject *choices* would need to be stored in a separate table. There are almost certainly traps awaiting the unwary here ... . Consider a pupil's chosen subjects changing during a year: perhaps there is a different subject list in the two terms!

