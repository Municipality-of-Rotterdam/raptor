# Change Log: Raptor
All notable changes to this repo will be documented in this file.
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this repo adheres to [Semantic Versioning](http://semver.org/).

## [0.2.0] - 2025-09-26
Removed the WikiGenerator keyvault from DevOps CI/CD pipelines.

### **Changed**
- The keys WikiId and WikiSecret are moved from the SharedKeyvault to the AmlProdGroup.

## [0.1.1] - 2025-08-28
Fix package repo ci/cd and remove double prompts.

### **Fixed**
- Fixed package repo ci/cd (whitespace issue in config.yml)
- Remove double prompts for name and email

## [0.1.0] - 2025-08-28
Rework project repo batch endpoint and scheduled pipeline.

### **Changed**
- Simplify creation of multiple environments or components by using for-loops
- Creating new project repo based on scheduled pipeline results in working aml pipelinejob (within GemeenteRotterdam environment)
- Use replacetokens devops extension replacing own ugly code
- Rearrange parts of batch endpoint and scheduled pipeline to prevent duplicate code
- Remove many parameters which already could be called as variable
### **Fixed**
- Update ChangedFiles devops extension to version 2

## [0.0.5] - 2025-08-19
Added support for publishing Sphinx doucmentation to github pages.

### **Added**
- Support for Sphinx documentation to github pages.
### **Fixed**
- Fixed main workflow with new pre-commit and unittest settings.

## [0.0.4] - 2025-07-21
Added support for supplying user config.

### **Added**
- Support for supplying a user config.
### **Fixed**
- Update to newest mcr.microsoft.com/azureml base image.
- author name including email bug

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