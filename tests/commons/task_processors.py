def process_task_verification(task_steps):
    verifications = {}
    validation_steps = []
    for index, task_step in task_steps.items():
        # skip step verification if any of the dependant steps is failed
        depends_on = task_step.get('depends_on')
        if depends_on is not None:
            if not all(verifications[i] for i in depends_on):
                verifications[index] = False
                continue
        handler = task_step['handler']
        step_errors = handler(task_step['params'])
        step_passed = not step_errors
        item = {
            'description': task_step['description'],
            'step_passed': step_passed,
            'meta': {'errors': step_errors} if step_errors else {}
        }
        validation_steps.append(item)
        verifications[index] = step_passed
    return validation_steps
