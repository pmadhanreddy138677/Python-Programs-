from django.db import models


class Institution(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    # Comma-separated, e.g. "example.edu,students.example.edu". Blank = any email accepted.
    allowed_email_domains = models.CharField(
        max_length=500, blank=True,
        help_text="Comma-separated allowed email domains. Leave blank to accept any email (development only).",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def domain_list(self):
        return [d.strip().lower().lstrip("@") for d in self.allowed_email_domains.split(",") if d.strip()]

    def email_allowed(self, email):
        domains = self.domain_list()
        if not domains:
            return True
        return email.rsplit("@", 1)[-1].lower() in domains


class Department(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["institution", "name"], name="uniq_department_per_institution")]

    def __str__(self):
        return self.name


class Program(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="programs")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="programs")
    name = models.CharField(max_length=150)
    duration_years = models.PositiveSmallIntegerField(default=4)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["institution", "name"], name="uniq_program_per_institution")]

    def __str__(self):
        return self.name
