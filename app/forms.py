from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, FileField, BooleanField, DecimalField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from app.models import User

# Leave type choices for LeaveRequestForm
LEAVE_TYPE_CHOICES = [
    ('COC', 'COC'),
    ('Vacation Leave', 'Vacation Leave'),
    ('Mandatory/Forced Leave', 'Mandatory/Forced Leave'),
    ('Sick Leave', 'Sick Leave'),
    ('Maternity Leave', 'Maternity Leave'),
    ('Paternity Leave', 'Paternity Leave'),
    ('Special Privilege Leave', 'Special Privilege Leave'),
    ('Solo Parent Leave', 'Solo Parent Leave'),
    ('Study Leave', 'Study Leave'),
    ('10-Day VAWC Leave', '10-Day VAWC Leave'),
    ('Rehabilitation Privilege', 'Rehabilitation Privilege'),
    ('Special Leave Benefits for Women', 'Special Leave Benefits for Women'),
    ('Special Emergency (Calamity)', 'Special Emergency (Calamity)'),
    ('Adoption Leave', 'Adoption Leave'),
    ('Others', 'Others')
]

class RegistrationForm(FlaskForm):
    username = StringField('Username', 
                         validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email')
    password = PasswordField('Password', 
                           validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                   validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is already taken. Please choose a different one.')

    # The User model may be overriding our status, so ensure it in the form
    def get_user(self):
        user = User(
            username=self.username.data,
            email=self.email.data,
            status='Pending'  # This is crucial - ensure status is set explicitly
        )
        user.password = self.password.data
        return user

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class DocumentForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    office = SelectField('Office', choices=[], validators=[DataRequired()])
    classification = SelectField('Classification', choices=[
        ('', 'Select a classification'),
        ('Communications', 'Communications'),
        ('Payroll', 'Payroll'),
        ('Request', 'Request'),
        ('Others', 'Others')
    ])
    custom_classification = StringField('Enter Classification', 
        validators=[Length(max=20)],  # Add character limit
        description='Max 20 characters'  # Help text for users
    )
    barcode = StringField('Barcode', description="Unique barcode identifier (if applicable)")
    status = SelectField('Status', choices=[], validators=[DataRequired()])
    action_taken = SelectField('Action Taken', choices=[], validators=[DataRequired()])
    attachment = FileField('Attachment')
    remarks = TextAreaField('Remarks')
    recipient = SelectField('Forward To', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Submit')

class DeclineDocumentForm(FlaskForm):
    reason = TextAreaField('Reason for Declining', validators=[DataRequired()])
    submit = SubmitField('Decline')

class ForwardDocumentForm(FlaskForm):
    recipient = SelectField('Forward To', coerce=int, validators=[DataRequired()])
    action_taken = SelectField('Action Taken', choices=[
        ('Noted', 'Noted'),
        ('Signed', 'Signed'),
        ('Approved', 'Approved'),
        ('Verified', 'Verified'),
        ('For Review', 'For Review'),
        ('For Revision', 'For Revision'),
        ('Endorsed', 'Endorsed'),
        ('Filed', 'Filed')
    ], validators=[DataRequired()])
    remarks = TextAreaField('Remarks')
    submit = SubmitField('Forward')

class ResubmitDocumentForm(FlaskForm):
    action_taken = SelectField('Action Taken', choices=[
        ('Noted', 'Noted'),
        ('Signed', 'Signed'),
        ('Approved', 'Approved'),
        ('Verified', 'Verified'),
        ('For Review', 'For Review'),
        ('For Revision', 'For Revision'),
        ('Endorsed', 'Endorsed'),
        ('Filed', 'Filed')
    ], validators=[DataRequired()])
    remarks = TextAreaField('Remarks')
    submit = SubmitField('Resubmit')


class LeaveRequestForm(FlaskForm):
    employee_name = StringField('Employee Name', validators=[DataRequired(), Length(min=1, max=120)])
    office = SelectField('Office', choices=[], validators=[DataRequired()])
    leave_type = SelectField('Type', choices=[], validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[Optional()], format='%Y-%m-%d')
    end_date = DateField('End Date', validators=[Optional()], format='%Y-%m-%d')
    barcode = StringField('Barcode')
    remarks = TextAreaField('Remarks')
    submit = SubmitField('Create Leave Record')

class EWPForm(FlaskForm):
    employee_name = StringField('Name', validators=[DataRequired(), Length(min=1, max=120)])
    office = SelectField('Office', choices=[], validators=[DataRequired()])
    barcode = StringField('Barcode')
    amount = DecimalField('Amount', places=2, rounding=None, validators=[DataRequired()])
    purpose = TextAreaField('Purpose', validators=[Optional()])
    remarks = TextAreaField('Remarks', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('For Computation', 'For Computation'),
        ('Pending', 'Pending'),
        ('Released', 'Released')
    ], validators=[Optional()])
    submit = SubmitField('Create EWP')

class EmployeeForm(FlaskForm):
    bio_number = StringField('Biometric', validators=[DataRequired()])
    employee_name = StringField('Name', validators=[DataRequired(), Length(min=1, max=120)])
    office = SelectField('Office', choices=[], validators=[DataRequired()])
    position = SelectField('Position', choices=[
        ('Job Order Worker', 'Job Order Worker'),
        ('Contract of Service', 'Contract of Service')
    ], validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('Active', 'Active'),
        ('Inactive', 'Inactive')
    ], validators=[DataRequired()])
    submit = SubmitField('Add Employee')

# Batch Action Forms
class BatchDeclineDocumentForm(FlaskForm):
    reason = TextAreaField('Reason for Declining', validators=[DataRequired()], 
                          render_kw={"placeholder": "Enter reason for declining all selected documents"})
    submit = SubmitField('Decline Selected Documents')

class BatchForwardDocumentForm(FlaskForm):
    recipient = SelectField('Forward To', coerce=int, validators=[DataRequired()])
    action_taken = SelectField('Action Taken', choices=[
        ('Noted', 'Noted'),
        ('Signed', 'Signed'),
        ('Approved', 'Approved'),
        ('Verified', 'Verified'),
        ('For Review', 'For Review'),
        ('For Revision', 'For Revision'),
        ('Endorsed', 'Endorsed'),
        ('Filed', 'Filed')
    ], validators=[DataRequired()])
    remarks = TextAreaField('Remarks', render_kw={"placeholder": "Optional remarks for all selected documents"})
    submit = SubmitField('Forward Selected Documents')
