# Change Log: Raptor
All notable changes to this repo will be documented in this file.
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this repo adheres to [Semantic Versioning](http://semver.org/).

## [0.0.3] - 2025-07-09
Fixed file cleanup after conditional prompt. Added CI tests for Github repo variant.

### **Added**
- CI tests for Github repo variant
### **Fixed**
- File cleanup after conditional prompt now happens before committing the template files.

## [0.0.2] - 2025-07-09
CI/CD fixes.

### **Added**
- test_requirements.txt for github CI/CD
### **Changed**
- updated poetry and cookiecutter version in test_requirements.txt
### **Fixed**
- default input values for local_extensions.py
- repo_name default value for project_repo in CI
- package_feed prompting for project_repo
- cookiecutter.organisation_name variable


## [0.0.1] - 2025-07-08
First version of the Raptor cookiecutter template.