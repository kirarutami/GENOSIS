# Pastikan Anda telah menginstal owlready2: pip install owlready2
# Anda mungkin juga perlu menginstal Java Development Kit (JDK) agar HermiT reasoner berfungsi.
import owlready2
from owlready2 import *
import os # Digunakan untuk memeriksa apakah file ada
import logging # Untuk mengontrol output logger Owlready2
import shutil # Untuk memeriksa keberadaan java (Python 3.3+)
import sys # Untuk Tee dan redirection
import traceback # Untuk mencetak traceback lengkap
from datetime import datetime # Untuk timestamp di log

# Menonaktifkan beberapa peringatan Owlready2 yang mungkin tidak relevan untuk output pengguna
logging.getLogger("owlready2").setLevel(logging.ERROR) 

class Tee(object):
    """
    Objek file-like yang menulis ke beberapa file sekaligus.
    Digunakan untuk mencatat output ke file dan menampilkannya di konsol.
    """
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(str(obj)) 
            f.flush() 
    def flush(self):
        for f in self.files:
            f.flush()
    def isatty(self): 
        return False

def log_class_definitions(world, current_onto, relevant_namespace_iris):
    """Logs class definitions from relevant namespaces."""
    print(f"\n--- Class Definitions from Relevant Namespaces in Ontology: {current_onto.name} ---")
    classes_found = False
    # Iterate all classes in the loaded ontologies
    for cls in world.classes(): 
        # Filter for named classes within the relevant namespaces
        # Exclude OWL built-ins unless they are in relevant_namespace_iris
        # Exclude anonymous classes (Restrictions, LogicalClassConstructs, EnumeratedClass constructs) and PropertyClasses
        if isinstance(cls, ThingClass) and hasattr(cls, "namespace") and cls.namespace and \
           cls.namespace.base_iri in relevant_namespace_iris and \
           not (isinstance(cls, owlready2.class_construct.Restriction) or \
                isinstance(cls, owlready2.class_construct.LogicalClassConstruct) or \
                (hasattr(cls, 'one_of') and cls.one_of) or \
                isinstance(cls, owlready2.prop.PropertyClass)): # Ensure it's not a property class

            classes_found = True
            print(f"\n  Class: {cls.name} (IRI: {cls.iri}, Namespace: {cls.namespace.base_iri})")
            if cls.label: print(f"    Label: {', '.join(cls.label)}")
            if cls.comment: print(f"    Comment: {', '.join(cls.comment)}")

            # Direct Superclasses (named ones and significant constructs)
            named_superclasses = []
            other_super_constructs = []
            # cls.is_a contains direct superclasses and superclass expressions
            for super_entity in cls.is_a:
                if isinstance(super_entity, ThingClass):
                    # Check if it's a named class (not a pure construct and not a property class)
                    if not (isinstance(super_entity, owlready2.class_construct.Restriction) or \
                            isinstance(super_entity, owlready2.class_construct.LogicalClassConstruct) or \
                            (hasattr(super_entity, 'one_of') and super_entity.one_of) or \
                            isinstance(super_entity, owlready2.prop.PropertyClass)):
                        # Add namespace prefix if it's not from the OWL namespace and different from current ontology's default
                        ns_prefix = ""
                        if super_entity.namespace != owl and hasattr(super_entity.namespace, 'name') and super_entity.namespace.name:
                             # Avoid redundant prefix for the main ontology's own namespace
                             if current_onto.namespace and super_entity.namespace.name != current_onto.namespace.name:
                                ns_prefix = f"{super_entity.namespace.name}:"
                        named_superclasses.append(f"{ns_prefix}{super_entity.name}")
                    # Log anonymous superclass constructs if they are not owl.Thing
                    elif super_entity != owl.Thing: 
                        other_super_constructs.append(str(super_entity))
            
            if named_superclasses:
                print(f"    Direct Named Superclasses: {', '.join(named_superclasses)}")
            if other_super_constructs: 
                 print(f"    Other Superclass Expressions (is_a): {', '.join(other_super_constructs)}")


            # Equivalent Classes (named ones or constructs)
            equivalent_definitions = []
            for eq_construct in cls.equivalent_to:
                # Check if it's a named class (not a pure construct and not a property class)
                if isinstance(eq_construct, ThingClass) and \
                   not (isinstance(eq_construct, owlready2.class_construct.Restriction) or \
                        isinstance(eq_construct, owlready2.class_construct.LogicalClassConstruct) or \
                        (hasattr(eq_construct, 'one_of') and eq_construct.one_of) or \
                        isinstance(eq_construct, owlready2.prop.PropertyClass)):
                    ns_prefix = ""
                    if eq_construct.namespace != owl and hasattr(eq_construct.namespace, 'name') and eq_construct.namespace.name:
                         if current_onto.namespace and eq_construct.namespace.name != current_onto.namespace.name:
                            ns_prefix = f"{eq_construct.namespace.name}:"
                    equivalent_definitions.append(f"{ns_prefix}{eq_construct.name}")
                else: 
                    # For anonymous constructs or built-in types
                    equivalent_definitions.append(str(eq_construct)) 
            if equivalent_definitions:
                print(f"    Equivalent to: {', '.join(equivalent_definitions)}")
            
    if not classes_found:
        print("  No user-defined Classes found in the relevant namespaces.")
    print("\n--- End of Class Definitions ---")


def log_property_definitions(world, current_onto, relevant_namespace_iris):
    """Logs object and data property definitions from relevant namespaces."""
    print(f"\n--- Object Property Definitions from Relevant Namespaces in Ontology: {current_onto.name} ---")
    properties_found = False
    for op in world.object_properties():
        if op.namespace.base_iri in relevant_namespace_iris:
            properties_found = True
            print(f"\n  Object Property: {op.name} (IRI: {op.iri}, Namespace: {op.namespace.base_iri})")
            if op.label: print(f"    Label: {', '.join(op.label)}")
            if op.comment: print(f"    Comment: {', '.join(op.comment)}")
            if op.domain: print(f"    Domain: {[d.name if hasattr(d, 'name') else str(d) for d in op.domain]}")
            if op.range: print(f"    Range: {[r.name if hasattr(r, 'name') else str(r) for r in op.range]}")
            
            characteristics = [str(char) for char in op.is_a if isinstance(char, owlready2.prop.PropertyClass) or (isinstance(char, ThingClass) and char.namespace == owl)]
            if characteristics: print(f"    Characteristics: {characteristics}")
            
            super_props = list(op.ancestors(include_self=False))
            relevant_super_props = [sp for sp in super_props if sp != owl.topObjectProperty]
            if relevant_super_props: print(f"    Super-properties: {[sp.name for sp in relevant_super_props]}")
    if not properties_found:
        print("  No Object Properties found in the relevant namespaces.")

    print(f"\n--- Data Property Definitions from Relevant Namespaces in Ontology: {current_onto.name} ---")
    properties_found = False
    for dp in world.data_properties():
        if dp.namespace.base_iri in relevant_namespace_iris:
            properties_found = True
            print(f"\n  Data Property: {dp.name} (IRI: {dp.iri}, Namespace: {dp.namespace.base_iri})")
            if dp.label: print(f"    Label: {', '.join(dp.label)}")
            if dp.comment: print(f"    Comment: {', '.join(dp.comment)}")
            if dp.domain: print(f"    Domain: {[d.name if hasattr(d, 'name') else str(d) for d in dp.domain]}")
            if dp.range: print(f"    Range: {[str(r) for r in dp.range]}") 
            
            characteristics = [str(char) for char in dp.is_a if isinstance(char, owlready2.prop.PropertyClass) or (isinstance(char, ThingClass) and char.namespace == owl)]
            if characteristics: print(f"    Characteristics: {characteristics}")

            super_props = list(dp.ancestors(include_self=False))
            relevant_super_props = [sp for sp in super_props if sp != owl.topDataProperty]
            if relevant_super_props: print(f"    Super-properties: {[sp.name for sp in relevant_super_props]}")
    if not properties_found:
        print("  No Data Properties found in the relevant namespaces.")
    print("\n--- End of Property Definitions ---")

def check_functional_property_violations(world, relevant_namespace_iris):
    """Explicitly checks for functional property violations from relevant namespaces."""
    print("\n--- Explicit Functional Property Violation Check (Relevant Namespaces) ---")
    violations_found = False
    for ind in world.individuals():
        # Check Functional Object Properties
        for op_class in world.object_properties(): 
            if op_class.namespace.base_iri in relevant_namespace_iris and owl.FunctionalProperty in op_class.is_a: 
                values = op_class[ind] 
                if not isinstance(values, list): values = [values] 
                if values and values[0] is not None and len(values) > 1: 
                    violations_found = True
                    print(f"  VIOLATION: Individual '{ind.name}' has more than one value for functional Object Property '{op_class.name}': {[str(v) for v in values]}")
        
        # Check Functional Data Properties
        for dp_class in world.data_properties(): 
            if dp_class.namespace.base_iri in relevant_namespace_iris and owl.FunctionalProperty in dp_class.is_a: 
                values = dp_class[ind] 
                if not isinstance(values, list): values = [values]
                if values and values[0] is not None and len(values) > 1:
                    violations_found = True
                    print(f"  VIOLATION: Individual '{ind.name}' has more than one value for functional Data Property '{dp_class.name}': {[str(v) for v in values]}")

    if not violations_found:
        print("  No functional property violations explicitly detected from relevant namespaces.")
    print("--- End of Functional Property Check ---")


def check_consistency_with_explanation(ontology_file, log_file_path="consistency_log.txt"):
    """
    Checks ontology consistency using HermiT and provides details on inconsistencies.
    Output is also logged to log_file_path.
    Assumes all data (TBox and ABox/instances) are in ontology_file.
    """
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    user_defined_relevant_namespace_iris = [
        "http://example.org/gsmfo.owl#", 
        "http://saralutami.org/OnlineSocialNetworkSites#",
        "http://saralutami.org/MicrobloggingPlatforms#",
        "http://saralutami.org/MediaContentSharingSites#",
        "http://saralutami.org/OnlineForumsBlogs#",
        "http://saralutami.org/GSMFO#"
    ]

    try:
        with open(log_file_path, 'w', encoding='utf-8') as log_file:
            log_file.write(f"Ontology Consistency Check Log Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write("===================================================================\n\n")
            
            tee_stdout = Tee(original_stdout, log_file)
            tee_stderr = Tee(original_stderr, log_file) 
            sys.stdout = tee_stdout
            sys.stderr = tee_stderr

            world = World() 
            onto = None 

            try:
                print(f"Loading ontology from file: {ontology_file}")
                ontology_uri = "file://" + ontology_file.replace("\\", "/")
                onto = world.get_ontology(ontology_uri).load()
                
                all_relevant_namespaces = set(user_defined_relevant_namespace_iris)
                if onto and onto.namespace and onto.namespace.base_iri:
                    all_relevant_namespaces.add(onto.namespace.base_iri)
                
                relevant_namespaces_list = list(all_relevant_namespaces)
                # Log class definitions first
                log_class_definitions(world, onto, relevant_namespaces_list)
                # Then log property definitions
                log_property_definitions(world, onto, relevant_namespaces_list) 

                print("\nSynchronizing with HermiT reasoner (HermiT output will be logged below if debug > 0)...")
                with world: 
                    sync_reasoner(infer_property_values=True, debug=1) 

                print("\nChecking consistency...")
                inconsistent_classes = list(world.inconsistent_classes())

                check_functional_property_violations(world, relevant_namespaces_list)

                if not inconsistent_classes:
                    print("\n✅ Ontology IS CONSISTENT (no inconsistent classes found and no global inconsistency error).")
                    nothing_instances = list(owl.Nothing.instances(world=world))
                    if nothing_instances:
                        print("\n   WARNING: Although no classes are inconsistent, owl.Nothing has the following instances (this should not happen):")
                        for ind_nothing in nothing_instances:
                            print(f"    - {ind_nothing.name}")
                    return True
                else:
                    print("\n❌ Ontology IS INCONSISTENT. Inconsistent classes found (TBox or due to ABox):")
                    for cls_item in inconsistent_classes: # Renamed cls to cls_item to avoid conflict with outer scope cls
                        print(f" - {cls_item.name if hasattr(cls_item, 'name') else str(cls_item)}")
                    
                    print("\n   Attempting to find individuals possibly related to inconsistent classes:")
                    for cls_item_detail in inconsistent_classes: # Renamed cls to cls_item_detail
                        cls_name = cls_item_detail.name if hasattr(cls_item_detail, 'name') else str(cls_item_detail)
                        if cls_item_detail == owl.Nothing:
                            print(f"   - Class owl.Nothing detected as inconsistent. This indicates a fundamental contradiction.")
                            print("     Checking for individuals that might be members of owl.Nothing:")
                            problematic_individuals = list(owl.Nothing.instances(world=world))
                            if problematic_individuals:
                                for ind in problematic_individuals:
                                    print(f"     - Individual {ind.name} is a member of owl.Nothing!")
                                    print(f"       Types of {ind.name}: {ind.is_a}")
                                    print(f"       Properties of {ind.name}:")
                                    for prop, value_list in ind.get_properties().items():
                                        for value in value_list if isinstance(value_list, list) else [value_list]:
                                            print(f"         - {prop.name}: {value}")
                            else:
                                print("     - No individuals explicitly inferred as members of owl.Nothing currently (might be a pure TBox inconsistency).")
                        else:
                            print(f"   - For inconsistent class {cls_name}:")
                            related_individuals = list(cls_item_detail.instances(world=world))
                            if related_individuals:
                                for individual in related_individuals:
                                    print(f"     - Individual {individual.name} is listed as an instance of inconsistent class {cls_name}.")
                            else:
                                print(f"     - No individuals found that are direct members of {cls_name}.")
                    return False

            except owlready2.base.OwlReadyInconsistentOntologyError as e:
                print(f"\n❌ Ontology IS GLOBALLY INCONSISTENT (most likely due to ABox/individuals): {str(e)}")
                
                print("\n   Searching for individuals that are members of owl.Nothing (strong indication of ABox inconsistency cause):")
                found_problematic_individual_in_error_handling = False
                if world: 
                    problematic_individuals = list(owl.Nothing.instances(world=world))
                    if problematic_individuals:
                        for individual in problematic_individuals:
                            found_problematic_individual_in_error_handling = True
                            print(f"   - PROBLEMATIC individual found: {individual.name} (inferred as a member of owl.Nothing)")
                            print(f"     Types of {individual.name}: {individual.is_a}")
                            print(f"     Properties of {individual.name}:")
                            for prop, value_list in individual.get_properties().items():
                                for value in value_list if isinstance(value_list, list) else [value_list]:
                                     print(f"       - {prop.name}: {value}")
                    
                if not found_problematic_individual_in_error_handling:
                    print("   - No specific individuals detected as members of owl.Nothing directly through standard iteration.")
                    print("     The inconsistency might be more complex. The Java error message (if any, in the message above) might provide clues.")

                if world:
                    inconsistent_classes_after_error = list(world.inconsistent_classes())
                    if inconsistent_classes_after_error:
                        print("\n   Inconsistent classes also detected (possibly related to the global error):")
                        for cls_err in inconsistent_classes_after_error:
                            print(f"   - {cls_err.name if hasattr(cls_err, 'name') else str(cls_err)}")
                return False

            except Exception as e:
                print(f"\n⚠️ An other error occurred during consistency check: {str(e)}")
                traceback.print_exc() 
                print("Please ensure Java Development Kit (JDK) is installed and its path is correctly configured.")
                print("Also ensure the ontology file is valid and accessible.")
                return False
            
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        print(f"\nConsistency check process finished. Full log saved to: {log_file_path}")


def main():
    print("""
===================================================================
  ONTOLOGY & INDIVIDUAL CONSISTENCY CHECKER (HERMIT/PELLET)
===================================================================
""")

    ontology_file_path = r"D:\thesis\Global Ontology\fixed global\GSMFO-withoutCase.owl" 
    log_file_name = "consistency_check_log.txt"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file_full_path = os.path.join(script_dir, log_file_name)

    print(f"Detailed output will be logged to: {log_file_full_path}\n")

    if not (os.path.exists(ontology_file_path) and os.path.isfile(ontology_file_path) and ontology_file_path.lower().endswith((".owl", ".rdf", ".xml"))):
        print(f"Ontology file not found or format not supported: {ontology_file_path}")
        try:
            with open(log_file_full_path, 'w', encoding='utf-8') as lf:
                lf.write(f"ERROR: Ontology file not found or format not supported: {ontology_file_path}\n")
        except Exception as e_log:
            print(f"Could not write initial error to log file: {e_log}")
        return
    
    print(f"\nOntology file to be checked: {ontology_file_path}")
    
    check_consistency_with_explanation(ontology_file_path, log_file_full_path)

if __name__ == "__main__":
    default_java_path = r"C:\Program Files\Java\jdk-11\bin\java.exe" 
    try:
        java_accessible_via_path = bool(shutil.which("java"))
        java_home_set = bool(os.getenv("JAVA_HOME"))

        if not java_accessible_via_path and not java_home_set:
            if os.path.exists(default_java_path):
                print(f"Info: Setting owlready2.JAVA_EXE to: {default_java_path}")
                owlready2.JAVA_EXE = default_java_path
            else:
                print(f"Warning: Java not detected in PATH, JAVA_HOME not set, and default path '{default_java_path}' not found.")
                print("Please ensure Java Development Kit (JDK) is installed and accessible.")
        elif not java_accessible_via_path and java_home_set:
             print(f"Info: JAVA_HOME is set to '{os.getenv('JAVA_HOME')}', but 'java' was not found in PATH. Owlready2 will attempt to use JAVA_HOME.")
        else:
            print("Info: Java detected via system PATH or JAVA_HOME.")

    except ImportError:
        if os.path.exists(default_java_path):
            print(f"Info: Setting owlready2.JAVA_EXE to (shutil not available): {default_java_path}")
            owlready2.JAVA_EXE = default_java_path
        else:
            print("Warning (shutil not available): Ensure Java is installed and accessible. Default path not found.")
    except Exception as e_java_setup:
        print(f"Error during Java configuration attempt: {e_java_setup}")
    main()
