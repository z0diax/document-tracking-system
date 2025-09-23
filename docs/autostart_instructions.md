# Auto-Start Instructions

1. Create a new `.bat` file:
   ```
   @echo off
   cd /c:/Users/User/projects/document-tracking-system
   python run.py
   ```

2. Open **Task Scheduler**, select **Create Task**, name it, enable **Run whether user is logged on or not**.

3. Under **Triggers**, choose **At startup**.

4. Under **Actions**, browse for your `.bat` file and save.

> Important: This runs only when the system is on. Code cannot execute if the computer is turned off.
