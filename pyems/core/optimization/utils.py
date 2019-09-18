
import numpy
import pyomo.kernel 


def recursive_element_search(container):

    constraint_list = []
    variable_list = []
    objective = None

    for element in container:
        if isinstance(element, pyomo.kernel.objective):
            if element.active:
                objective = str(element.expr)

        elif isinstance(element, pyomo.kernel.constraint):
            constraint_list.append(str(element.expr))

        elif isinstance(element, pyomo.kernel.variable):
            domain = str(element.domain_type).split('.')[-1].replace("'>", '')
            var_fields = [element.name, element.bounds, domain, element.fixed, element.value]
            variable_list.append(', '.join([str(field) for field in var_fields]))

        elif isinstance(element, pyomo.kernel.constraint_list):
            constraint_list.append('Constraint list:')

            nested_obj, nested_con, nested_var = recursive_element_search(container=element)
            if nested_obj is not None:
                objective = nested_obj
            constraint_list = constraint_list + nested_con
            variable_list = variable_list + nested_var

            constraint_list.append('')

        elif isinstance(element, pyomo.kernel.constraint_dict):
            constraint_list.append('Constraint dict:')

            nested_obj, nested_con, nested_var = recursive_element_search(container=element.values())
            if nested_obj is not None:
                objective = nested_obj
            constraint_list = constraint_list + nested_con
            variable_list = variable_list + nested_var

            constraint_list.append('')

        elif isinstance(element, pyomo.kernel.variable_list):
            variable_list.append('Variable list:')

            nested_obj, nested_con, nested_var = recursive_element_search(container=element)
            if nested_obj is not None:
                objective = nested_obj
            constraint_list = constraint_list + nested_con
            variable_list = variable_list + nested_var

            variable_list.append('')

        elif isinstance(element, pyomo.kernel.variable_dict):
            variable_list.append('Variable dict:')

            nested_obj, nested_con, nested_var = recursive_element_search(container=element.values())
            if nested_obj is not None:
                objective = nested_obj
            constraint_list = constraint_list + nested_con
            variable_list = variable_list + nested_var

            variable_list.append('')
            pass

    return objective, constraint_list, variable_list


def readable_pyomo_model(optimization_model):

    first_container = []

    for label in optimization_model.user_defined_attributes:
        first_container.append(optimization_model.__dict__[label])

    objective, constraint_list, variable_list = recursive_element_search(container=first_container)

    constraints = '    ' + '\n    '.join(constraint_list)
    variables = '    ' + '\n    '.join(variable_list)

    readable_model = (
        f"Pyomo optimization model:"
        f"\n\nObjective:\n    {objective}"
        f"\n\nConstraints:\n{constraints}"
        f"\n\nVariables:\n{variables}"
    )

    return readable_model


def combine_positive_negative_variables(positive, negative, error_messagge, tol=1e-5):
        """Combines two positive variables (all values >= 0) into one. For any
        time (index) v1 >= 0 and the other v2 == 0 otherwise this function would
        raise an exception.

        This function is thought to recombine an original variable explited in two
        for optimization purposes, i.e., the power flow into the battery. We can
        split the flow in charging and discharging both >= 0. To recombine it we
        use this function. Note that the battery cannot be charged and discharged
        at the same time, for that reason we check the above condition.

        Args:
            positive (array_like; float): Variable to be the positive part of the
                                          recombined one.
            negative (array_like; float): Variable to be the negative part of the
                                          recombined one.
            error_message (string): Message to display in the exception in case
                                    they check was not pass.

        Returns:
            variable (array; float): Return the recombined variable.

        Raise:
            ValueError: when v1 >= 0 and v2 == 0
        """

        positive = numpy.array(positive)
        negative = numpy.array(negative)

        positive[(-1 * tol < positive) & (positive < 0)] = 0
        negative[(-1 * tol < negative) & (negative < 0)] = 0

        # Checks correct inputs

        if any([v < 0 for v in positive]):
            raise ValueError(error_messagge)
        if any([v < 0 for v in negative]):
            raise ValueError(error_messagge)
        if any([bool(a) and bool(b) for a, b in zip(positive, negative)]):
            raise ValueError(error_messagge)

        # Combine values

        variable = positive - negative

        return variable