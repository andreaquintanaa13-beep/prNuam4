from django import forms
from .models import Calificacion

class CalificacionForm(forms.ModelForm):
    class Meta:
        model = Calificacion
        fields = ['fecha', 'mercado', 'ano', 'descripcion', 'factor_actualizado']
        widgets = {
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'mercado': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'ano': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '2000',
                'max': '2030',
                'required': True
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Descripción de la calificación',
                'maxlength': '100'
            }),
            'factor_actualizado': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.corredor = kwargs.pop('corredor', None)
        super().__init__(*args, **kwargs)
        
        # Opciones para mercado
        self.fields['mercado'].widget.choices = [
            ('', 'Seleccionar mercado'),
            ('ACC', 'Acciones'),
            ('CFI', 'CFI'), 
            ('FM', 'Fondos Mutuos'),
        ]

    def save(self, commit=True):
        calificacion = super().save(commit=False)
        
        # Asignar el corredor
        if self.corredor:
            calificacion.fk_id_corredor = self.corredor
        
        if commit:
            calificacion.save()
            
        return calificacion