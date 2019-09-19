# Python Energy Management System (pyems) Toolkit for Smart Building

## Description

Energy Management System (EMS) Toolkit for Smart Buildings based on Python. An EMS is a program that make decisions on how to operate different devices of the building (battery SOC, AC temperature, when to switch on the washing machine…) based on the knowledge of the system (building model, historical data, forecasts…) and user comfort preferences. This repository provides tools to simplify and speed up the development of your own custom EMS. 

## Modes of operation

This toolkit provides two well differentiated modes of operation:
+ Simulation: Reproduce the operation of the EMS Based on a data set. This mode is useful for research purposes as well as to tune the parameters of the EMS and make economical evaluations. This can be run without any third-party software apart from the required python packages and optimization solver.  
+ Operation: Deployment of an EMS that actually controls a system. The system automatically collects the data from different sources (databases, APIs, csv…), run an optimization model and returns the results. This mode requires the use of a third-party tools to work. 
+ Deployment
An Automation System (AS) like Home Assistance (HASS) could be used to monitor an operate the building. This means collecting data of the different devices (PV panels, building load, temperature…) into a permanent storage like a database and actuate building’s devices, switching them on/off or controlling a certain parameter. Task schedulers like Windows task scheduler or Linux cron jobs could also be used in conjunction with the AS or without it, to run the EMS at a determine frequency. The function of the latter group could be also assumed by the Automation System. 

## Features

The main features of the pyems are:
+ Modular construction: the pyems toolkit is not a final product but instead a toolkit that provides different entities (classes) and functions that can be combined together to create your own custom EMS. 
+ I/O tools: allow a custom data flow while ease the input/output of data from/to different data sources like csv files, InfluxDB, APIs…
+ Integration of forecast tools: like Facebook Prophet or scikit-learn.
+ Optimization: MIP optimization based on Pyomo (python based optimization modeling language) and GLPK open source solver.

## Mian Entities

The main entities (classes) of the core package are:
+ Simulation: singleton (only one instance is allowed) that control the execution process and stores general and temporal parameters of the execution like the number of time periods ahead to optimize or the timestep resolution.
+ System: represents a physical system like a house, an office building or a power system. The system is a container for other system components like electrical/thermal loads or generators. 
+ System components: blocks to build the system. At the moment the development is focused on electrical components. The intention is to include thermal components in the future. Current components are based on generic Forecasters.
+ Forecaster: element that takes some parameters or historical data and issue a forecast of the characteristic parameters of a system component for a specific period of time. 
+ Data handler: this class is in charge of the data input/output flow. This entity provides, on request, the data to the different components of the system previous to the optimization.
+ Optimizer: Translates the system definition (System instance) into a mathematical optimization model (Pyomo model). Then it solves de model, checks the validity and return the results.

## Forecasting models
We can distinguish three types black, grey or white box models. The difference between them strives in the different knowledge the Forecaster has about the components.
We say we are using a white box when the mathematical model is based on physical equation and the parameters that governs those equations are known with certainty.
If the parameters are not certain but estimated with some technique, we say is a grey model. 
A black box represents a generic mathematical algorithm, that doesn’t know anything about the system but only is feed with some generic data, in this case time series, and produce an output.
The any object that black box model in which some historical data series

