from django.db import models

#TODO: Note that I would actually prefer a text input with datalist
# to a select input!
GRADE_CHOICES = [
    ('1+', '1+'), ('1', '1'), ('1-', '1-'),
    ('2+', '2+'), ('2', '2'), ('2-', '2-'),
    ('3+', '3+'), ('3', '3'), ('3-', '3-'),
    ('4+', '4+'), ('4', '4'), ('4-', '4-'),
    ('5+', '5+'), ('5', '5'), ('5-', '5-'),
    ('6', '6'),
    ('nt', 'nicht teilgenommen'),
    ('nb', 'nicht bewertbar'),
    ('/', 'nicht gewählt'),
    ('*', 'keine Note')
]

class Grade(models.Model):
    pid = models.ForeignKey(
        'Pupil',
        on_delete=models.CASCADE,
        db_index=False
    )
    
    sid = models.ForeignKey(
        'Subject',
        on_delete=models.CASCADE,
        db_index=False
    )
    
    grade = models.CharField(
        max_length=20,
        choices=GRADE_CHOICES,
        default=None,
        null=True,
        blank=True
    )
    entry_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        db_index=False,
        null=True
    )
    
    entry_time = models.DateTimeField()
#TODO: Do I need the class & stream, too?


#TODO:
### These models should be in the base app!

class Pupil(models.Model):
    pid = models.CharField(
        max_length=6, primary_key=True)
    name = models.CharField(
        max_length=50)
    klass = models.CharField(
        max_length=6)
    stream = models.CharField(
        max_length=6)

class User(models.Model):
    tid = models.CharField(
        max_length=6, primary_key=True)
    name = models.CharField(
        max_length=50)
    sort_name = models.CharField(
        max_length=20)
        
class Subject(models.Model):
    sid = models.CharField(
        max_length=10, primary_key=True)
    name = models.CharField(
        max_length=30)
