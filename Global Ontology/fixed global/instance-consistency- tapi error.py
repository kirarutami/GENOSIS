# Ensure you have owlready2 installed: pip install owlready2
# You might also need to install Java Development Kit (JDK) for the HermiT reasoner to work.
import owlready2
from owlready2 import * # Imports Thing, AllDisjoint, sync_reasoner_hermit etc.
import owlready2.reasoning # Explicitly import the reasoning submodule
import os 
import logging 
import shutil 
import sys 
import traceback 
from datetime import datetime 
import tempfile 
import shlex 

# --- DIAGNOSTIC BLOCK START ---
print("--- DIAGNOSTIC: Initializing and Checking owlready2.reasoning ---")
try:
    if hasattr(owlready2, 'reasoning') and owlready2.reasoning:
        print(f"  owlready2.reasoning module successfully imported.")
        if hasattr(owlready2.reasoning, '__file__'):
            print(f"  owlready2.reasoning.__file__: {owlready2.reasoning.__file__}")
        else:
            print("  owlready2.reasoning does not have a __file__ attribute (might be a built-in or complex module).")

        # Check for expected attributes
        expected_attrs = ['HERMIT_JAR', 'JAVA_OPTIONS', 'PELLET_JAR'] # Add others if needed
        for attr_name in expected_attrs:
            if hasattr(owlready2.reasoning, attr_name):
                # Try to get the value, but be careful if it's not a simple constant
                try:
                    attr_value = getattr(owlready2.reasoning, attr_name)
                    print(f"  Found attribute owlready2.reasoning.{attr_name}: {attr_value}")
                except Exception as e_getattr:
                    print(f"  Found attribute owlready2.reasoning.{attr_name}, but could not get its value: {e_getattr}")
            else:
                print(f"  Attribute owlready2.reasoning.{attr_name} NOT FOUND.")
        
        # print("\n  Full directory of owlready2.reasoning:")
        # for item in dir(owlready2.reasoning):
        # print(f"    {item}") # This can be very verbose
    else:
        print("  ERROR: owlready2.reasoning module is not available after import.")
except Exception as e_diag_init:
    print(f"  ERROR during diagnostic block: {e_diag_init}")
    traceback.print_exc()
print("--- DIAGNOSTIC BLOCK END ---\n")
# --- DIAGNOSTIC BLOCK END ---


logging.getLogger("owlready2").setLevel(logging.ERROR) 

class Tee(object):
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

def log_namespaces_and_prefixes(world, current_onto, relevant_namespace_iris):
    print("\n--- Ontology Namespaces and Prefixes ---")
    if current_onto and current_onto.base_iri:
        print(f"  Main ontology ({current_onto.name}) Base IRI: {current_onto.base_iri}")
    else:
        print(f"  Main ontology ({current_onto.name if current_onto else 'N/A'}) does not have a clear Base IRI.")
    print("  Prefixes known to Owlready2 (may not be exhaustive for all original xmlns definitions):")
    try:
        if hasattr(world.graph, "namespaces"): 
            prefix_map = {prefix: str(ns) for prefix, ns in world.graph.namespaces()}
        elif hasattr(world, "sparql_rules_manager") and hasattr(world.sparql_rules_manager, "sparql_namespace_manager") and \
             hasattr(world.sparql_rules_manager.sparql_namespace_manager, "namespace_manager") and \
             hasattr(world.sparql_rules_manager.sparql_namespace_manager.namespace_manager, "_Graph__namespace"):
            prefix_map = world.sparql_rules_manager.sparql_namespace_manager.namespace_manager._Graph__namespace
        else:
            prefix_map = {}
        if prefix_map:
            for prefix, ns_iri in prefix_map.items():
                print(f"    - Prefix '{prefix}': {ns_iri}")
        else:
            print("    - No prefixes explicitly registered or accessible in the default namespace manager.")
    except Exception as e:
        print(f"    - Could not retrieve prefixes: {e}")
    print("\n  Namespaces detected from entities within 'relevant_namespace_iris':")
    detected_ns = set()
    for onto_to_check in list(world.ontologies.values()): 
        if onto_to_check.namespace and onto_to_check.namespace.base_iri in relevant_namespace_iris:
            detected_ns.add(onto_to_check.namespace.base_iri)
        for cls in onto_to_check.classes():
            if cls.namespace and cls.namespace.base_iri in relevant_namespace_iris:
                detected_ns.add(cls.namespace.base_iri)
        for prop in list(onto_to_check.object_properties()) + list(onto_to_check.data_properties()):
            if prop.namespace and prop.namespace.base_iri in relevant_namespace_iris:
                detected_ns.add(prop.namespace.base_iri)
        for ind in onto_to_check.individuals():
            if ind.namespace and ind.namespace.base_iri in relevant_namespace_iris:
                detected_ns.add(ind.namespace.base_iri)
    if detected_ns:
        for ns_iri in sorted(list(detected_ns)):
            print(f"    - {ns_iri}")
    else:
        print("    - No namespaces from entities matching 'relevant_namespace_iris' were found.")
    print("--- End of Namespaces and Prefixes ---")

def log_class_definitions(world, current_onto, relevant_namespace_iris):
    print(f"\n--- Class Definitions from Relevant Namespaces in Ontology: {current_onto.name if current_onto else 'N/A'} ---")
    classes_found = False
    for cls in world.classes(): 
        if isinstance(cls, ThingClass) and hasattr(cls, "namespace") and cls.namespace and \
           cls.namespace.base_iri in relevant_namespace_iris and \
           not (isinstance(cls, owlready2.class_construct.Restriction) or \
                isinstance(cls, owlready2.class_construct.LogicalClassConstruct) or \
                (hasattr(cls, 'one_of') and cls.one_of) or \
                isinstance(cls, owlready2.prop.PropertyClass)):
            classes_found = True
            print(f"\n  Class: {cls.name} (IRI: {cls.iri}, Namespace: {cls.namespace.base_iri})")
            if cls.label: print(f"    Label: {', '.join(cls.label)}")
            if cls.comment: print(f"    Comment: {', '.join(cls.comment)}")
            named_superclasses = []
            other_super_constructs = []
            for super_entity in cls.is_a:
                if isinstance(super_entity, ThingClass):
                    if not (isinstance(super_entity, owlready2.class_construct.Restriction) or \
                            isinstance(super_entity, owlready2.class_construct.LogicalClassConstruct) or \
                            (hasattr(super_entity, 'one_of') and super_entity.one_of) or \
                            isinstance(super_entity, owlready2.prop.PropertyClass)):
                        ns_prefix = ""
                        if super_entity.namespace != owl and hasattr(super_entity.namespace, 'name') and super_entity.namespace.name:
                            if not (current_onto and current_onto.namespace and super_entity.namespace.base_iri == current_onto.namespace.base_iri):
                                ns_prefix = f"{super_entity.namespace.name}:"
                        named_superclasses.append(f"{ns_prefix}{super_entity.name}")
                elif super_entity != owl.Thing: 
                    other_super_constructs.append(str(super_entity))
            if named_superclasses:
                print(f"    Direct Named Superclasses: {', '.join(named_superclasses)}")
            if other_super_constructs: 
                print(f"    Other Superclass Expressions (is_a): {', '.join(other_super_constructs)}")
            equivalent_definitions = []
            for eq_construct in cls.equivalent_to:
                if isinstance(eq_construct, ThingClass) and \
                   not (isinstance(eq_construct, owlready2.class_construct.Restriction) or \
                        isinstance(eq_construct, owlready2.class_construct.LogicalClassConstruct) or \
                        (hasattr(eq_construct, 'one_of') and eq_construct.one_of) or \
                        isinstance(eq_construct, owlready2.prop.PropertyClass)):
                    ns_prefix = ""
                    if eq_construct.namespace != owl and hasattr(eq_construct.namespace, 'name') and eq_construct.namespace.name:
                        if not (current_onto and current_onto.namespace and eq_construct.namespace.base_iri == current_onto.namespace.base_iri):
                            ns_prefix = f"{eq_construct.namespace.name}:"
                    equivalent_definitions.append(f"{ns_prefix}{eq_construct.name}")
                else: 
                    equivalent_definitions.append(str(eq_construct)) 
            if equivalent_definitions:
                print(f"    Equivalent to: {', '.join(equivalent_definitions)}")
            disjoint_axioms_logged = False
            for disjoint_statement in cls.disjoints(): 
                disjoint_classes_in_statement = [e.name if hasattr(e, 'name') else str(e) for e in disjoint_statement.entities if e != cls]
                if disjoint_classes_in_statement:
                    if not disjoint_axioms_logged:
                        print(f"    Disjoint With (from Disjoint axioms where this class participates):")
                        disjoint_axioms_logged = True
                    direct_disjoints = []
                    for other_cls in disjoint_statement.entities:
                        if other_cls != cls: 
                             direct_disjoints.append(other_cls.name if hasattr(other_cls, 'name') else str(other_cls))
                    if direct_disjoints:
                         print(f"      - Axiom implies disjoint with: {', '.join(direct_disjoints)}")
    if not classes_found:
        print("  No user-defined Classes found in the relevant namespaces.")
    print("\n--- End of Class Definitions ---")

def log_property_definitions(world, current_onto, relevant_namespace_iris):
    print(f"\n--- Object Property Definitions from Relevant Namespaces in Ontology: {current_onto.name if current_onto else 'N/A'} ---")
    properties_found = False
    for op in world.object_properties():
        if op.namespace and op.namespace.base_iri in relevant_namespace_iris:
            properties_found = True
            print(f"\n  Object Property: {op.name} (IRI: {op.iri}, Namespace: {op.namespace.base_iri})")
            if op.label: print(f"    Label: {', '.join(op.label)}")
            if op.comment: print(f"    Comment: {', '.join(op.comment)}")
            if op.domain: print(f"    Domain: {[d.name if hasattr(d, 'name') else str(d) for d in op.domain]}")
            if op.range: print(f"    Range: {[r.name if hasattr(r, 'name') else str(r) for r in op.range]}")
            characteristics = [str(char).split('.')[-1] for char in op.is_a if isinstance(char, owlready2.prop.PropertyClass) or (isinstance(char, ThingClass) and char.namespace == owl and char != owl.ObjectProperty)]
            if characteristics: print(f"    Characteristics: {characteristics}")
            super_props = [sp for sp in op.is_a if isinstance(sp, ObjectProperty) and sp != owl.topObjectProperty and sp != op]
            if super_props: print(f"    Super-properties (direct): {[sp.name for sp in super_props]}")
    if not properties_found:
        print("  No Object Properties found in the relevant namespaces.")
    print(f"\n--- Data Property Definitions from Relevant Namespaces in Ontology: {current_onto.name if current_onto else 'N/A'} ---")
    properties_found = False
    for dp in world.data_properties():
        if dp.namespace and dp.namespace.base_iri in relevant_namespace_iris:
            properties_found = True
            print(f"\n  Data Property: {dp.name} (IRI: {dp.iri}, Namespace: {dp.namespace.base_iri})")
            if dp.label: print(f"    Label: {', '.join(dp.label)}")
            if dp.comment: print(f"    Comment: {', '.join(dp.comment)}")
            if dp.domain: print(f"    Domain: {[d.name if hasattr(d, 'name') else str(d) for d in dp.domain]}")
            if dp.range: print(f"    Range: {[str(r) for r in dp.range]}") 
            characteristics = [str(char).split('.')[-1] for char in dp.is_a if isinstance(char, owlready2.prop.PropertyClass) or (isinstance(char, ThingClass) and char.namespace == owl and char != owl.DatatypeProperty)]
            if characteristics: print(f"    Characteristics: {characteristics}")
            super_props = [sp for sp in dp.is_a if isinstance(sp, DataProperty) and sp != owl.topDataProperty and sp != dp]
            if super_props: print(f"    Super-properties (direct): {[sp.name for sp in super_props]}")
    if not properties_found:
        print("  No Data Properties found in the relevant namespaces.")
    print("\n--- End of Property Definitions ---")

def check_functional_property_violations(world, relevant_namespace_iris):
    print("\n--- Explicit Functional Property Violation Check (Relevant Namespaces) ---")
    violations_found = False
    for ind in world.individuals():
        if not (hasattr(ind, "namespace") and ind.namespace and ind.namespace.base_iri in relevant_namespace_iris):
            continue 
        for op_class in world.object_properties(): 
            if op_class.namespace and op_class.namespace.base_iri in relevant_namespace_iris and owl.FunctionalProperty in op_class.is_a: 
                values = op_class[ind] 
                if not isinstance(values, list): values = [values] 
                actual_values = [v for v in values if v is not None]
                if len(actual_values) > 1: 
                    violations_found = True
                    print(f"  VIOLATION: Individual '{ind.name}' has more than one value for functional Object Property '{op_class.name}': {[str(v.name) if hasattr(v, 'name') else str(v) for v in actual_values]}")
        for dp_class in world.data_properties(): 
            if dp_class.namespace and dp_class.namespace.base_iri in relevant_namespace_iris and owl.FunctionalProperty in dp_class.is_a: 
                values = dp_class[ind] 
                if not isinstance(values, list): values = [values]
                actual_values = [v for v in values if v is not None]
                if len(actual_values) > 1:
                    violations_found = True
                    print(f"  VIOLATION: Individual '{ind.name}' has more than one value for functional Data Property '{dp_class.name}': {[str(v) for v in actual_values]}")
    if not violations_found:
        print("  No functional property violations explicitly detected from relevant namespaces.")
    print("--- End of Functional Property Check ---")

def log_all_relevant_individual_details_before_reasoning(world, current_onto, relevant_namespace_iris):
    print(f"\n--- Details of All Relevant Individuals (Before Reasoning) ---")
    individuals_found = False
    for ind in world.individuals():
        ind_namespace_iri = ind.namespace.base_iri if hasattr(ind, "namespace") and ind.namespace else None
        if not (ind_namespace_iri and ind_namespace_iri in relevant_namespace_iris):
            continue
        individuals_found = True
        print(f"\n  Individual: {ind.name} (IRI: {ind.iri}, Namespace: {ind_namespace_iri})")
        print(f"    Asserted Types (is_a):")
        types_list = list(ind.is_a) 
        if types_list:
            for rdf_type in types_list:
                type_name = rdf_type.name if hasattr(rdf_type, 'name') else str(rdf_type)
                type_ns = rdf_type.namespace.base_iri if hasattr(rdf_type, 'namespace') and rdf_type.namespace else 'N/A'
                print(f"      - {type_name} (IRI: {rdf_type.iri}, Namespace: {type_ns})")
        else:
            print("      - No explicit types (implicitly owl:Thing).")
        if len(types_list) >= 2:
            print("    Disjointness Check Among Asserted Types:")
            disjoint_pairs_found = False
            type_iris_set = {t.iri for t in types_list if isinstance(t, ThingClass)}
            for i in range(len(types_list)):
                type1 = types_list[i]
                if not isinstance(type1, ThingClass): continue
                for disjoint_axiom in type1.disjoints(): 
                    for type2_in_axiom in disjoint_axiom.entities:
                        if type2_in_axiom != type1 and type2_in_axiom.iri in type_iris_set:
                            type2_obj = next((t for t in types_list if t.iri == type2_in_axiom.iri), None)
                            if type2_obj and type1.iri < type2_obj.iri : 
                                print(f"      - Types '{type1.name}' and '{type2_obj.name}' are declared disjoint.")
                                disjoint_pairs_found = True
            if not disjoint_pairs_found:
                print("      - No asserted type pairs are explicitly declared disjoint by owl:disjointWith.")
    if not individuals_found:
        print("  No individuals found in relevant namespaces to log before reasoning.")
    print(f"--- End of Details of All Relevant Individuals (Before Reasoning) ---")

def log_explicit_instance_consistency_check(world, current_onto, relevant_namespace_iris):
    print("\n--- Instance Details & Consistency Check (Relevant Namespaces, After Reasoning) ---")
    instances_found_in_relevant_namespaces = False
    any_inconsistency_found_in_instances = False
    nothing_individuals_set = set(owl.Nothing.instances(world=world))
    if nothing_individuals_set:
        print(f"  DEBUG: Individuals inferred as owl.Nothing by reasoner: {[i.name for i in nothing_individuals_set if hasattr(i, 'name')]}")
    else:
        print(f"  DEBUG: No individuals inferred as owl.Nothing by reasoner.")
    for ind in world.individuals():
        ind_namespace_iri = ind.namespace.base_iri if hasattr(ind, "namespace") and ind.namespace else None
        if not (ind_namespace_iri and ind_namespace_iri in relevant_namespace_iris):
            continue
        instances_found_in_relevant_namespaces = True
        print(f"\n  Instance: {ind.name} (IRI: {ind.iri}, Namespace: {ind_namespace_iri})")
        if ind.label: print(f"    Label: {', '.join(ind.label)}")
        if ind.comment: print(f"    Comment: {', '.join(ind.comment)}")
        direct_types_str = []
        is_inconsistent_instance = ind in nothing_individuals_set
        for rdf_type in ind.is_a: 
            type_name = rdf_type.name if hasattr(rdf_type, 'name') else str(rdf_type)
            ns_prefix = ""
            if hasattr(rdf_type, 'namespace') and rdf_type.namespace != owl :
                if rdf_type.namespace.name and rdf_type.namespace.name != "owl": 
                    if not (current_onto and current_onto.namespace and rdf_type.namespace.base_iri == current_onto.namespace.base_iri):
                         ns_prefix = f"{rdf_type.namespace.name}:"
            direct_types_str.append(f"{ns_prefix}{type_name}")
        if direct_types_str:
            print(f"    Types (After Reasoning): {', '.join(direct_types_str)}")
        else:
            print("    Types (After Reasoning): None (implicitly owl:Thing)")
        print(f"    Properties:")
        has_any_property_for_this_individual = False
        for op in world.object_properties():
            try: values = op[ind] 
            except Exception: values = [] 
            if values: 
                has_any_property_for_this_individual = True
                prop_name_str = op.name
                ns_prefix_prop = ""
                if hasattr(op, 'namespace') and op.namespace != owl:
                    if op.namespace.name and op.namespace.name != "owl":
                        if not (current_onto and current_onto.namespace and op.namespace.base_iri == current_onto.namespace.base_iri):
                            ns_prefix_prop = f"{op.namespace.name}:"
                prop_display_name = f"{ns_prefix_prop}{prop_name_str}"
                actual_values = values if isinstance(values, list) else [values]
                value_strs = []
                for value in actual_values:
                    if value is not None: 
                        if isinstance(value, owlready2.entity.Thing): 
                            value_name_str = value.name
                            ns_prefix_val = ""
                            if hasattr(value, 'namespace') and value.namespace != owl:
                                if value.namespace.name and value.namespace.name != "owl":
                                     if not (current_onto and current_onto.namespace and value.namespace.base_iri == current_onto.namespace.base_iri):
                                        ns_prefix_val = f"{value.namespace.name}:"
                            value_strs.append(f"{ns_prefix_val}{value_name_str} (IRI: {value.iri})")
                        else: 
                            value_strs.append(f'"{str(value)}"') 
                if value_strs:
                    print(f"      - {prop_display_name}: {', '.join(value_strs)}")
        for dp in world.data_properties():
            try: values = dp[ind]
            except Exception: values = []
            if values: 
                has_any_property_for_this_individual = True
                prop_name_str = dp.name
                ns_prefix_prop = ""
                if hasattr(dp, 'namespace') and dp.namespace != owl:
                    if dp.namespace.name and dp.namespace.name != "owl":
                        if not (current_onto and current_onto.namespace and dp.namespace.base_iri == current_onto.namespace.base_iri):
                            ns_prefix_prop = f"{dp.namespace.name}:"
                prop_display_name = f"{ns_prefix_prop}{prop_name_str}"
                actual_values = values if isinstance(values, list) else [values]
                value_strs = []
                for value in actual_values:
                    if value is not None: 
                        if isinstance(value, datetime): value_strs.append(f'"{value.isoformat()}"^^xsd:dateTime')
                        elif isinstance(value, bool): value_strs.append(f'"{str(value).lower()}"^^xsd:boolean')
                        elif isinstance(value, (int, float)):
                            xsd_type = "xsd:integer" if isinstance(value, int) else "xsd:decimal" 
                            value_strs.append(f'"{str(value)}"^^{xsd_type}')
                        else: value_strs.append(f'"{str(value)}"') 
                if value_strs:
                    print(f"      - {prop_display_name}: {', '.join(value_strs)}")
        if not has_any_property_for_this_individual:
            print("      - No asserted object or data properties found for this individual.")
        if is_inconsistent_instance: 
            any_inconsistency_found_in_instances = True
            print(f"    🔴 INCONSISTENT INSTANCE: This instance ({ind.name}) is inferred to be an instance of owl.Nothing.")
        print("-" * 10) 
    if not instances_found_in_relevant_namespaces:
        print("  No individuals found in the specified relevant namespaces.")
    if any_inconsistency_found_in_instances:
        print("\n  Overall Instance Consistency (Relevant Namespaces): At least one instance from relevant namespaces is inconsistent (member of owl.Nothing).")
    elif instances_found_in_relevant_namespaces: 
        print("\n  Overall Instance Consistency (Relevant Namespaces): All checked instances from relevant namespaces appear consistent (not members of owl.Nothing).")
    print("--- End of Instance Details & Consistency Check (After Reasoning) ---")
    return any_inconsistency_found_in_instances 

def run_minimal_consistency_test():
    print("\n--- Running Minimal In-Script Consistency Test ---")
    temp_world = World(filename = ":memory:") 
    with temp_world:
        temp_ns_iri = "http://temporary.org/test_ontology#"
        temp_onto = temp_world.get_ontology(temp_ns_iri) 
        with temp_onto: 
            class TestClassA(Thing): pass
            class TestClassB(Thing): pass
            AllDisjoint([TestClassA, TestClassB]) 
            test_individual = TestClassA("MinimalConflictingIndividual", namespace = temp_onto)
            test_individual.is_a.append(TestClassB)
            print(f"  Minimal Test: Individual '{test_individual.name}' (IRI: {test_individual.iri}) created.")
            print(f"    Asserted types: {[t.name for t in test_individual.is_a]}")
            print("  Minimal Test: Owlready2 Internal Pre-Reasoner Check:")
            pre_reasoner_minimal_inconsistency = False
            types_check = test_individual.is_a
            if len(types_check) >= 2:
                type1, type2 = types_check[0], types_check[1] 
                is_disjoint_internal = False
                class_a_in_temp_onto = temp_onto.TestClassA
                class_b_in_temp_onto = temp_onto.TestClassB
                for disjoint_axiom in class_a_in_temp_onto.disjoints():
                    if class_b_in_temp_onto in disjoint_axiom.entities: 
                        is_disjoint_internal = True; break
                if is_disjoint_internal:
                    print(f"    PRE-REASONER INCONSISTENCY (Minimal Test): Individual '{test_individual.name}' is instance of '{type1.name}' and '{type2.name}' which are disjoint.")
                    pre_reasoner_minimal_inconsistency = True
            if not pre_reasoner_minimal_inconsistency:
                print("    No obvious disjointness violation found by Owlready2 internal check for minimal test.")
            print("  Minimal Test: Synchronizing with HermiT reasoner...")
            reasoning_succeeded_minimal = False
            hermit_command_minimal = ""
            temp_file_path_minimal = ""
            try:
                fd, temp_file_path_minimal = tempfile.mkstemp(suffix=".owl", prefix="owlready_hermit_minimal_")
                os.close(fd)
                temp_onto.save(file=temp_file_path_minimal, format="rdfxml")
                
                # Access HERMIT_JAR and JAVA_OPTIONS via owlready2.reasoning
                # Access JAVA_EXE via owlready2.JAVA_EXE as it's set there
                hermit_jar_path_val = owlready2.reasoning.HERMIT_JAR # Corrected access
                hermit_dir_path_val = os.path.dirname(hermit_jar_path_val)
                cp = "%s%s%s" % (hermit_dir_path_val, os.pathsep, hermit_jar_path_val)
                
                command = [owlready2.JAVA_EXE] + owlready2.reasoning.JAVA_OPTIONS + ["-cp", cp, "org.semanticweb.HermiT.cli.CommandLine", "-c", "-O", "-D", "-I", "file:///%s" % temp_file_path_minimal.replace(os.sep, '/'), "-Y"]
                hermit_command_minimal = " ".join(shlex.quote(s) for s in command) 
                
                print(f"    * Owlready2 (Minimal Test) * Running HermiT with command:")
                print(f"      {hermit_command_minimal}")
                print(f"    * Owlready2 (Minimal Test) * Using temporary file: {temp_file_path_minimal}")
                print(f"    >>> ACTION (Minimal Test): If this test fails, try running the above HermiT command manually in your terminal using the specified temporary file.")
                
                sync_reasoner_hermit(temp_world, infer_property_values=False, debug=1, ontology_file_for_hermit=temp_file_path_minimal)
                reasoning_succeeded_minimal = True 
            except subprocess.CalledProcessError as e_minimal_sub:
                print(f"    ERROR (Minimal Test): HermiT subprocess failed with exit code {e_minimal_sub.returncode}.")
                if e_minimal_sub.output: print(f"      HermiT output (stderr/stdout):\n{e_minimal_sub.output.decode(errors='replace')}")
            except OwlReadyInconsistentOntologyError: 
                print(f"    SUCCESS (Minimal Test - OwlReadyInconsistentOntologyError): HermiT reported the ontology as inconsistent as expected.")
                reasoning_succeeded_minimal = True 
            except Exception as e_minimal:
                print(f"    ERROR during minimal test reasoning: {e_minimal}")
                traceback.print_exc(file=sys.stdout)
            finally:
                if reasoning_succeeded_minimal:
                    print("  Minimal Test: Status After Reasoning (if HermiT ran without crashing):")
                    if test_individual in owl.Nothing.instances(world=temp_world):
                        print(f"    SUCCESS (Minimal Test): Individual '{test_individual.name}' IS an instance of owl.Nothing.")
                    else:
                        print(f"    FAILURE (Minimal Test): Individual '{test_individual.name}' IS NOT an instance of owl.Nothing.")
                if temp_file_path_minimal and os.path.exists(temp_file_path_minimal) and not owlready2.reasoning.KEEP_TMP_FILES:
                    try: os.remove(temp_file_path_minimal)
                    except Exception as e_rm_tmp: print(f"    Warning: Could not remove minimal test temporary file {temp_file_path_minimal}: {e_rm_tmp}")
                elif temp_file_path_minimal and os.path.exists(temp_file_path_minimal):
                     print(f"    Minimal test temporary file kept at: {temp_file_path_minimal}")
    print("--- End of Minimal In-Script Consistency Test ---")

def check_consistency_with_explanation(ontology_file, log_file_path="consistency_log.txt"):
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
            run_minimal_consistency_test()
            print("\n--- Starting Check for Main Ontology File ---")
            for onto_in_world_name in list(default_world.ontologies.keys()):
                if onto_in_world_name != "http://www.w3.org/2002/07/owl": 
                    try:
                        print(f"  Attempting to destroy pre-existing ontology: {onto_in_world_name}")
                        default_world.ontologies[onto_in_world_name].destroy()
                    except Exception as e_destroy:
                        print(f"  Warning: Could not destroy existing ontology {onto_in_world_name} from default_world: {e_destroy}")
            world = default_world 
            onto = None 
            try:
                print(f"Loading ontology from file: {ontology_file}")
                abs_ontology_file_path = os.path.abspath(ontology_file)
                ontology_uri = "file://" + abs_ontology_file_path.replace("\\", "/").replace(" ", "%20")
                onto = world.get_ontology(ontology_uri).load()
                if not onto:
                    print(f"FAILED to load ontology. Please check the file path and format.")
                    return False
                all_relevant_namespaces = set(user_defined_relevant_namespace_iris)
                if onto and onto.namespace and onto.namespace.base_iri:
                    all_relevant_namespaces.add(onto.namespace.base_iri)
                for imp_onto in onto.imported_ontologies:
                    if imp_onto.namespace and imp_onto.namespace.base_iri:
                        all_relevant_namespaces.add(imp_onto.namespace.base_iri) 
                relevant_namespaces_list = list(all_relevant_namespaces)
                print(f"\nChecking against relevant namespaces (includes main ontology and its imports): {relevant_namespaces_list}")
                log_namespaces_and_prefixes(world, onto, relevant_namespaces_list)
                log_class_definitions(world, onto, relevant_namespaces_list)
                log_property_definitions(world, onto, relevant_namespaces_list) 
                log_all_relevant_individual_details_before_reasoning(world, onto, relevant_namespaces_list)
                print("\n--- Owlready2 Internal Pre-Reasoner Inconsistency Check (Main Ontology) ---")
                pre_reasoner_inconsistencies_found_main = False
                for ind_check in world.individuals(): 
                    ind_check_ns_iri = ind_check.namespace.base_iri if hasattr(ind_check, "namespace") and ind_check.namespace else None
                    if not (ind_check_ns_iri and ind_check_ns_iri in relevant_namespaces_list):
                        continue
                    types_check = ind_check.is_a
                    if len(types_check) >= 2:
                        processed_pairs = set() 
                        for i in range(len(types_check)):
                            for j in range(i + 1, len(types_check)):
                                type1 = types_check[i]
                                type2 = types_check[j]
                                pair_key = tuple(sorted((type1.iri, type2.iri)))
                                if pair_key in processed_pairs: continue
                                processed_pairs.add(pair_key)
                                if isinstance(type1, ThingClass) and isinstance(type2, ThingClass):
                                    is_directly_disjoint = False
                                    for disjoint_axiom in type1.disjoints(): 
                                        if type2 in disjoint_axiom.entities:
                                            is_directly_disjoint = True; break
                                    if not is_directly_disjoint: 
                                         for disjoint_axiom in type2.disjoints():
                                            if type1 in disjoint_axiom.entities:
                                                is_directly_disjoint = True; break
                                    if is_directly_disjoint:
                                        print(f"  PRE-REASONER INCONSISTENCY DETECTED (Main Ontology - Owlready2): Individual '{ind_check.name}' (IRI: {ind_check.iri})")
                                        print(f"    is an instance of '{type1.name}' (IRI: {type1.iri})")
                                        print(f"    and an instance of '{type2.name}' (IRI: {type2.iri}),")
                                        print(f"    which are declared disjoint.")
                                        pre_reasoner_inconsistencies_found_main = True
                if not pre_reasoner_inconsistencies_found_main:
                    print("  No obvious disjointness violations found by Owlready2's internal check for the main ontology.")
                print("--- End of Owlready2 Internal Pre-Reasoner Inconsistency Check (Main Ontology) ---")
                print("\nSynchronizing with HermiT reasoner (Main Ontology)...")
                print("  IMPORTANT: The temporary file used by HermiT will be kept for manual inspection if keep_tmp_file=True.")
                print("  Look for a line like '* Owlready2 * Running HermiT...' in the log to find the command and temp file path.")
                main_hermit_temp_file_path = None 
                try:
                    fd_main, main_hermit_temp_file_path = tempfile.mkstemp(suffix=".owl", prefix="owlready_hermit_main_")
                    os.close(fd_main)
                    onto.save(file=main_hermit_temp_file_path, format="rdfxml")
                    
                    # Access HERMIT_JAR and JAVA_OPTIONS via owlready2.reasoning
                    # Access JAVA_EXE via owlready2.JAVA_EXE
                    hermit_jar_path_main_val = owlready2.reasoning.HERMIT_JAR
                    hermit_dir_path_main_val = os.path.dirname(hermit_jar_path_main_val)
                    cp_main = "%s%s%s" % (hermit_dir_path_main_val, os.pathsep, hermit_jar_path_main_val)
                    command_main = [owlready2.JAVA_EXE] + owlready2.reasoning.JAVA_OPTIONS + ["-cp", cp_main, "org.semanticweb.HermiT.cli.CommandLine", "-c", "-O", "-D", "-I", "file:///%s" % main_hermit_temp_file_path.replace(os.sep, '/'), "-Y"]
                    
                    print(f"    * Owlready2 (Main Ontology) * Will attempt to run HermiT with command (similar to):")
                    print(f"      {' '.join(shlex.quote(s) for s in command_main)}") 
                    print(f"    * Owlready2 (Main Ontology) * Using temporary file: {main_hermit_temp_file_path}")
                    print(f"    >>> ACTION (Main Ontology): If reasoning fails, try running the above HermiT command manually in your terminal using this temporary file.")
                    with world: 
                        sync_reasoner_hermit(world, infer_property_values=True, debug=1, ontology_file_for_hermit=main_hermit_temp_file_path)
                finally:
                    if main_hermit_temp_file_path and os.path.exists(main_hermit_temp_file_path) and not owlready2.reasoning.KEEP_TMP_FILES:
                        try: os.remove(main_hermit_temp_file_path)
                        except Exception: pass 
                    elif main_hermit_temp_file_path and os.path.exists(main_hermit_temp_file_path):
                        print(f"    Main ontology temporary file for HermiT kept at: {main_hermit_temp_file_path}")
                print("\n--- Status After Reasoning (Main Ontology) ---")
                log_explicit_instance_consistency_check(world, onto, relevant_namespaces_list) 
                print("\nChecking for inconsistent classes (Main Ontology)...")
                inconsistent_classes = list(world.inconsistent_classes()) 
                check_functional_property_violations(world, relevant_namespaces_list)
                final_nothing_instances = list(owl.Nothing.instances(world=world)) 
                if not inconsistent_classes and not final_nothing_instances:
                    print("\n✅ MAIN ONTOLOGY IS CONSISTENT.")
                    return True
                else:
                    print("\n❌ MAIN ONTOLOGY IS INCONSISTENT.")
                    if inconsistent_classes:
                        print("  Reason(s): Inconsistent classes found:")
                        for cls_item in inconsistent_classes:
                            print(f"    - Inconsistent Class: {cls_item.name} (IRI: {cls_item.iri})")
                    if final_nothing_instances:
                        print("  Reason(s): Individuals found to be members of owl.Nothing:")
                        for ind_nothing in final_nothing_instances:
                            print(f"    - Problematic Individual: {ind_nothing.name} (IRI: {ind_nothing.iri})")
                    print("\n  IMPORTANT NOTE FOR INCONSISTENCIES (Main Ontology):")
                    print("  If the 'Minimal In-Script Consistency Test' passed (detected inconsistency) but this main ontology check")
                    print("  fails to detect an expected inconsistency (e.g., for 'ConflictingEntity_001'),")
                    print("  the issue is very likely related to the parsing or specific structure of your OWL file ('GSMFO.owl').")
                    print("  Focus on IRI representations, namespace definitions in the OWL file, and the exact spelling/structure of disjointness axioms.")
                    print("  If the 'Owlready2 Internal Pre-Reasoner Inconsistency Check (Main Ontology)' found the issue, but HermiT didn't,")
                    print("  this points to a problem in the Owlready2-to-HermiT pipeline for your specific ontology.")
                    print(f"  >>> ACTION: Manually run the HermiT command (see above) using the temporary file: {main_hermit_temp_file_path if main_hermit_temp_file_path else 'Path not captured, enable keep_tmp_file in sync_reasoner'}")
                    print("  >>>         Capture any error output from HermiT directly from your terminal.")
                    return False
            except owlready2.base.OwlReadyInconsistentOntologyError as e:
                print(f"\n❌ MAIN ONTOLOGY IS GLOBALLY INCONSISTENT (OwlReadyInconsistentOntologyError raised by Owlready2):")
                error_message = str(e)
                print(f"  Error details from Owlready2: {error_message}")
                if hasattr(e, 'reasoner_output') and e.reasoner_output:
                    if e.reasoner_output not in error_message : 
                        print(f"  Explicitly printing e.reasoner_output:\n<<<<<<<<<< REASONER OUTPUT START >>>>>>>>>>\n{e.reasoner_output}\n<<<<<<<<<< REASONER OUTPUT END >>>>>>>>>>")
                else:
                    print(f"  e.reasoner_output was not available or empty.")
                print(f"  This error often means the reasoner (HermiT) failed to complete its process successfully.")
                print(f"  >>> ACTION: Manually run the HermiT command (see above) using the temporary file: {main_hermit_temp_file_path if main_hermit_temp_file_path else 'Path not captured, enable keep_tmp_file in sync_reasoner'}")
                print(f"  >>>         to see direct HermiT errors.")
                print(f"  Full Python traceback for this OwlReadyInconsistentOntologyError:")
                traceback.print_exc() 
                print("\n  Attempting to find individuals that are instances of owl.Nothing (post-OwlReadyInconsistentOntologyError):")
                found_problematic_individual_in_error_handling = False
                if world: 
                    try:
                        problematic_individuals = list(owl.Nothing.instances(world=world)) 
                        if problematic_individuals:
                            for individual in problematic_individuals:
                                found_problematic_individual_in_error_handling = True
                                print(f"  - PROBLEMATIC individual found (post-error): {individual.name} (inferred as a member of owl.Nothing)")
                        if not found_problematic_individual_in_error_handling:
                             print("  - No specific individuals detected as members of owl.Nothing directly after this error.")
                    except Exception as e_post_error:
                        print(f"  - Failed to retrieve owl.Nothing instances after OwlReadyInconsistentOntologyError: {e_post_error}")
                return False
            except Exception as e:
                print(f"\n⚠️ An other error occurred during main ontology consistency check: {str(e)}")
                traceback.print_exc() 
                return False
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        if not owlready2.reasoning.KEEP_TMP_FILES: 
            pass
        print(f"\nConsistency check process finished. Full log saved to: {log_file_path}")

def main():
    print("""
===================================================================
  ONTOLOGY & INDIVIDUAL CONSISTENCY CHECKER (HERMIT)
===================================================================
""")
    owlready2.reasoning.KEEP_TMP_FILES = True 
    print("INFO: owlready2.reasoning.KEEP_TMP_FILES is set to True. Temporary files for HermiT will be kept.")
    ontology_file_path = r"D:\thesis\Global Ontology\fixed global\GSMFO.owl" 
    log_file_name = "consistency_check_log.txt"
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError: 
        script_dir = os.getcwd() 
    log_file_full_path = os.path.join(script_dir, log_file_name)
    print(f"Detailed output will be logged to: {log_file_full_path}\n")
    if not (os.path.exists(ontology_file_path) and os.path.isfile(ontology_file_path) and ontology_file_path.lower().endswith((".owl", ".rdf", ".xml", ".ttl"))):
        error_msg = f"Ontology file not found or format not supported: {ontology_file_path}"
        print(error_msg)
        try:
            with open(log_file_full_path, 'w', encoding='utf-8') as lf:
                lf.write(f"ERROR: {error_msg}\n")
        except Exception as e_log:
            print(f"Could not write initial error to log file: {e_log}")
        return
    print(f"\nOntology file to be checked: {ontology_file_path}")
    check_consistency_with_explanation(ontology_file_path, log_file_full_path)

if __name__ == "__main__":
    default_java_path_windows = r"C:\Program Files\Java\jdk-11\bin\java.exe" 
    java_exe_configured = False
    # owlready2.JAVA_EXE is set here, making it globally available in the owlready2 module
    try:
        if shutil.which("java"): 
            owlready2.JAVA_EXE = shutil.which("java") 
            print(f"Info: Java detected via system PATH: {owlready2.JAVA_EXE}")
            java_exe_configured = True
        elif os.getenv("JAVA_HOME"): 
            java_home_path = os.getenv("JAVA_HOME")
            potential_java_exe = os.path.join(java_home_path, "bin", "java.exe" if os.name == 'nt' else "java")
            if os.path.exists(potential_java_exe):
                owlready2.JAVA_EXE = potential_java_exe 
                print(f"Info: Java detected via JAVA_HOME: {owlready2.JAVA_EXE}")
                java_exe_configured = True
            else:
                print(f"Warning: JAVA_HOME ('{java_home_path}') is set, but java executable not found there ('{potential_java_exe}').")
        if not java_exe_configured: 
            default_java_path_to_try = default_java_path_windows if os.name == 'nt' else None 
            if default_java_path_to_try and os.path.exists(default_java_path_to_try):
                owlready2.JAVA_EXE = default_java_path_to_try 
                print(f"Info: Java not in PATH or valid JAVA_HOME. Using default path: {owlready2.JAVA_EXE}")
                java_exe_configured = True
            else:
                 print(f"Warning: Java not detected in PATH, JAVA_HOME not valid, and default path ('{default_java_path_to_try if default_java_path_to_try else 'No default path for this OS'}') not found.")
        if not owlready2.JAVA_EXE: # Check if owlready2.JAVA_EXE ended up being None
             print("CRITICAL WARNING: owlready2.JAVA_EXE is not set. Attempting to set a default or use system found Java.")
             if java_exe_configured : pass
             elif default_java_path_windows and os.path.exists(default_java_path_windows) and os.name == 'nt': 
                 owlready2.JAVA_EXE = default_java_path_windows
                 print(f"Info: Fallback - Owlready2 will use Java executable at: {owlready2.JAVA_EXE}")
        if not owlready2.JAVA_EXE:
             print("CRITICAL WARNING: Java executable (owlready2.JAVA_EXE) could not be configured automatically and is not set.")
        elif owlready2.JAVA_EXE:
             print(f"Info: Owlready2 will use Java executable at: {owlready2.JAVA_EXE}")
    except ImportError: 
        print("Warning: 'shutil' module not available. Cannot check for 'java' in PATH automatically.")
        print("Please ensure Java is installed and accessible. Consider setting owlready2.JAVA_EXE manually.")
    except Exception as e_java_setup:
        print(f"Error during Java configuration attempt: {e_java_setup}")
    main()
