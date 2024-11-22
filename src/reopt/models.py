from django.db import models

class RunData(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return str(self.id) + " - " + self.name
