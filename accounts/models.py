from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [
        ('user', 'Normal User'),
        ('admin', 'Admin'),
        ('law_enforcement', 'Law Enforcement'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    email = models.EmailField(unique=True)
    
    def __str__(self):
        return self.username
