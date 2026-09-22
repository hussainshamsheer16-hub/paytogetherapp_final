import secrets
import string

from django.db import models
from django.conf import settings

# Create your models here.

def generate_join_code():
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))



class Tour(models.Model):

    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]




    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="tours"
        )

    join_code = models.CharField(
        max_length=8,
        unique=True,
        editable=False,
        default=generate_join_code,
    )


    title = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    image = models.ImageField(
        upload_to="tours/",
        blank=True,
        null=True
        )



    budget = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=0,
        )

    
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="planned"
    )


    created_at = models.DateTimeField(
        auto_now_add=True
        )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tour"
        verbose_name_plural = "Tours"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.join_code:
            self.join_code = generate_join_code()
        super().save(*args, **kwargs)


class TourMember(models.Model):
    tour = models.ForeignKey(
        Tour,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="joined_tours",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["joined_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tour", "user"],
                name="unique_tour_member",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.tour}"
