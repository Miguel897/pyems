# Energy Management System

Note: this toolkit is in a very preliminary state and some of the features mentioned here are not yet available.

Open Energy Management System (EMS) Toolkit for Smart Buildings based on Python. An EMS is a program that make decisions on how to operate different devices of the building (battery SOC, AC temperature, when to switch on the washing machine…) based on the knowledge of the system (building model, historical data, forecasts…) and user comfort preferences. This repository provides tools to simplify and ease the deployment of your own custom EMS.

This toolkit provides two different modes of operation:
+ Simulation: Reproduce the operation of the EMS Based on a data set. This mode is useful for research purposes as well as to tune the parameters of the EMS and make economical evaluations. This can be run without any third-party software apart from the required python packages and optimization solver.  
+ Operation: Deployment of an EMS that actually controls a system. The system automatically collects the data from different sources (databases, APIs, csv…), run an optimization model and returns the results. This mode requires the use of a third-party tools to work. 

## Features

The main features of the pyems are:
+ Modular construction: the pyems toolkit is not a final product but instead a toolkit that provides different entities (classes) and functions that can be combined together to create your own custom EMS. 
+ I/O tools: allow a custom data flow while ease the input/output of data from/to different data sources like csv files, InfluxDB, APIs…
+ Integration of forecast tools: like Facebook Prophet or scikit-learn.
+ Optimization: MIP optimization based on Pyomo (python based optimization modeling language) and GLPK open source solver.

## Documentation

In the docs folder you could find more documentation regarding the Toolkit.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

The required packages are:

```
DateTime pytz numpy pandas matplotlib Pyomo glpk pysolar fbprophet
```
Optional requirements:
```
influxdb
```

### Installing

The simpler approach is to copy the source file of project and create an environment. If you are using the fbprophet package to issue the forecasts then the Anaconda environments are strongly recommended due to some issue in the installation of pystan used by Anaconda.

Download the source files in a folder and create your own implementation project at the same level.

```
root_folder/
│
├── pyems/
│   ├── pyems/
│   └── other_files.*
│   
└── your_implementation/
    ├── main.py
    └── your_modules.py
```

Create an Anaconda environment:
```
conda create --name ems_env
```

Install the requirements:

```
conda install --file /path/to/pyems/requirements.txt
```

In the main.py include the following code:

```
import os
import sys
sys.path.append(os.path.abspath(r'..\pyems'))
import pyems.environ as ems
```

Now, in your main.py you can create the entities like this:
```
system = ems.System(name='your_system')
```

## Running the tests

The tests are located in the tests folder in the root of the repository. The tests are created with unittest.

```
pyems/
   ├── pyems/
   ├── tests/
   └── other_files.*
```

## Deployment

For real operation a third-party software mayb required. An Automation System (AS) like Home Assistance (HASS) could be used to monitor an operate the building. This means collecting data of the different devices (PV panels, building load, temperature…) into a permanent storage like a database and actuate building’s devices, switching them on/off or controlling a certain parameter. Task schedulers like Windows task scheduler or Linux cron jobs could also be used in conjunction with the AS or without it, to run the EMS at a determine frequency. The function of the latter group could be also assumed by the Automation System. 

## Built With

* [Pyomo](http://www.pyomo.org/) - Pyomo is a Python-based, open-source optimization modeling language
* [GLPK](https://www.gnu.org/software/glpk/) - GNU Linear Programming Kit
* [FB Prophet](https://facebook.github.io/prophet/docs/quick_start.html) - Forecasting tool developed by Facebook

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

The versioning follow the scheme major.minor.patch. Patch in general won't break the compatibility from one to another. Minor version changes probably creates backward compatibility issues. Major versions implies major changes in the stability and capability of the software.

## Authors

* **Miguel Angel Munoz** - *Main developer* 

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License

This project is licensed under the GNU General Public License v3 (GPLv3) - see the [LICENSE](LICENSE) file for details.

<!---
## Acknowledgments
For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 
--->
