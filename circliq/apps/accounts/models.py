from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("role", User.Role.STUDENT)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(role=User.Role.ADMIN, is_staff=True, is_superuser=True,
                     is_email_verified=True, is_approved=True)
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        FACULTY = "faculty", "Faculty"
        ADMIN = "admin", "Administrator"

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    institution = models.ForeignKey("institutions.Institution", on_delete=models.PROTECT,
                                    null=True, blank=True, related_name="users")
    department = models.ForeignKey("institutions.Department", on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="users")
    program = models.ForeignKey("institutions.Program", on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="users")
    academic_year = models.PositiveSmallIntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    # Faculty accounts stay unapproved until a staff member approves them.
    is_approved = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    # Self-deactivation (reversible by the user) vs. restriction by a campus admin (reversible only by an admin).
    deactivated_at = models.DateTimeField(null=True, blank=True)
    is_restricted = models.BooleanField(default=False)
    restriction_reason = models.CharField(max_length=200, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]
    objects = UserManager()

    class Meta:
        indexes = [models.Index(fields=["institution", "role"])]

    def __str__(self):
        return self.email

    @property
    def first_name(self):
        return self.full_name.split(" ")[0] if self.full_name else self.email.split("@")[0]

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_faculty(self):
        return self.role == self.Role.FACULTY

    @property
    def is_campus_admin(self):
        return self.role == self.Role.ADMIN
