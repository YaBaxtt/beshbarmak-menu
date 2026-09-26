from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("guest_name", "rating", "text")

    def clean_guest_name(self):
        return self.cleaned_data.get("guest_name", "").strip()

    def clean_text(self):
        text = self.cleaned_data.get("text", "").strip()
        if len(text) < 5:
            raise forms.ValidationError("Fikr kamida 5 ta belgidan iborat bo‘lsin.")
        return text
