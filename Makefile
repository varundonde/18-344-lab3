TARGET   = vm_test 

CXX      = g++
LINKER   = g++

CXXFLAGS = -Wall -g
LFLAGS   = -Wall  

SOURCES  := pte.cpp vm-provided.cpp ptab.cpp tlb.cpp \
            vm-student.cpp vm_test.cpp 
OBJECTS  := $(SOURCES:%.cpp=%.o)

TYPST ?= typst
ZIP ?= zip
SUBMISSION_ZIP := lab3-submission.zip
REPORT_ASSETS := $(wildcard report/figures/* report/*.csv)
SUBMISSION_FILES := Makefile $(wildcard *.cpp *.h) run_traces.py \
                    report/lab3-report.pdf $(wildcard traces/*.trace) traces/manifest.json

$(TARGET): $(OBJECTS)
	$(LINKER) $(OBJECTS) $(LFLAGS) -o $@

$(OBJECTS): %.o : %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

report/lab3-report.pdf: report/lab3-report.typ $(REPORT_ASSETS)
	$(TYPST) compile $< $@

.PHONY: submission
submission: report/lab3-report.pdf
	$(ZIP) -q -FS $(SUBMISSION_ZIP) $(SUBMISSION_FILES)

.PHONY: clean
clean:
	-rm $(OBJECTS)

.PHONY: cleanall 
cleanall: clean
	-rm $(TARGET)
