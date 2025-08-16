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

# --- MANUAL CONFIGURATION FOR HERMIT - USER TO VERIFY ---
USER_HERMIT_JAR_PATH = r"D:\thesis\.venv\lib\site-packages\owlready2\hermit\HermiT.jar" 
USER_JAVA_OPTIONS = ['-Xmx2000M'] 

try:
    if os.path.exists(USER_HERMIT_JAR_PATH):
        owlready2.reasoning.HERMIT_JAR = USER_HERMIT_JAR_PATH
        print(f"INFO: Manually set owlready2.reasoning.HERMIT_JAR to: {owlready2.reasoning.HERMIT_JAR}")
    else:
        print(f"WARNING: Manual HERMIT_JAR path not found: {USER_HERMIT_JAR_PATH}")
        print(f"         Owlready2 will attempt its default detection mechanism for HERMIT_JAR.")
        if not hasattr(owlready2.reasoning, 'HERMIT_JAR'): 
            owlready2.reasoning.HERMIT_JAR = None 

    owlready2.reasoning.JAVA_OPTIONS = USER_JAVA_OPTIONS
    print(f"INFO: Manually set owlready2.reasoning.JAVA_OPTIONS to: {owlready2.reasoning.JAVA_OPTIONS}")

except AttributeError as e_attr_config:
    print(f"ERROR during manual configuration: Could not set HERMIT_JAR or JAVA_OPTIONS on owlready2.reasoning module: {e_attr_config}")
except Exception as e_config:
    print(f"UNEXPECTED ERROR during manual configuration: {e_config}")
# --- END OF MANUAL CONFIGURATION ---


# --- DIAGNOSTIC BLOCK START ---
print("--- DIAGNOSTIC: Initializing and Checking owlready2.reasoning ---")
OWLREADY2_REASONING_VALID = False
try:
    if hasattr(owlready2, 'reasoning') and owlready2.reasoning:
        print(f"  owlready2.reasoning module successfully imported.")
        if hasattr(owlready2.reasoning, '__file__'):
            print(f"  owlready2.reasoning.__file__: {owlready2.reasoning.__file__}")
        else:
            print("  owlready2.reasoning does not have a __file__ attribute.")

        hermit_jar_path_diag = getattr(owlready2.reasoning, 'HERMIT_JAR', None)
        java_options_diag = getattr(owlready2.reasoning, 'JAVA_OPTIONS', None)

        if hermit_jar_path_diag:
            print(f"  Found owlready2.reasoning.HERMIT_JAR: {hermit_jar_path_diag}")
            if not os.path.exists(str(hermit_jar_path_diag)): 
                 print(f"    WARNING: Path for owlready2.reasoning.HERMIT_JAR does not exist: {hermit_jar_path_diag}")
                 hermit_jar_path_diag = None 
        else:
            print("  CRITICAL: Attribute owlready2.reasoning.HERMIT_JAR NOT FOUND or is None.")

        if java_options_diag is not None: 
            print(f"  Found owlready2.reasoning.JAVA_OPTIONS: {java_options_diag}")
        else:
            print("  CRITICAL: Attribute owlready2.reasoning.JAVA_OPTIONS NOT FOUND.")
        
        if hermit_jar_path_diag and java_options_diag is not None: 
            OWLREADY2_REASONING_VALID = True
            print("  Diagnostic: owlready2.reasoning appears to have valid HERMIT_JAR and JAVA_OPTIONS.")
        else:
            print("  CRITICAL DIAGNOSTIC: owlready2.reasoning is missing HERMIT_JAR or JAVA_OPTIONS, or HERMIT_JAR path is invalid.")
            
    else:
        print("  CRITICAL ERROR: owlready2.reasoning module is not available after import.")
        sys.exit("Exiting due to missing owlready2.reasoning module.")

except Exception as e_diag_init:
    print(f"  ERROR during diagnostic block: {e_diag_init}")
    traceback.print_exc()
    sys.exit("Exiting due to error in diagnostic block.")
print("--- DIAGNOSTIC BLOCK END ---\n")

if not OWLREADY2_REASONING_VALID:
    print("CRITICAL ERROR: Necessary Owlready2 reasoning components were not found or are invalid after diagnostics.")
    sys.exit("Exiting due to missing reasoning components.")


logging.getLogger("owlready2").setLevel(logging.ERROR) 

class Tee(object):
    def __init__(self, *files): self.files = files
    def write(self, obj):
        for f in self.files: f.write(str(obj)); f.flush() 
    def flush(self):
        for f in self.files: f.flush()
    def isatty(self): return False

def log_namespaces_and_prefixes(world, current_onto, relevant_namespace_iris):
    print("\n--- Ontology Namespaces and Prefixes ---")
    if current_onto and current_onto.base_iri: print(f"  Main ontology ({current_onto.name}) Base IRI: {current_onto.base_iri}")
    else: print(f"  Main ontology ({current_onto.name if current_onto else 'N/A'}) does not have a clear Base IRI.")
    print("  Prefixes known to Owlready2:")
    try:
        prefix_map = {prefix: str(ns) for prefix, ns in world.graph.namespaces()} if hasattr(world.graph, "namespaces") else {}
        if prefix_map:
            for prefix, ns_iri in prefix_map.items(): print(f"    - Prefix '{prefix}': {ns_iri}")
        else: print("    - No prefixes explicitly registered.")
    except Exception as e: print(f"    - Could not retrieve prefixes: {e}")
    print("\n  Namespaces detected from entities within 'relevant_namespace_iris':")
    detected_ns = set(ns_iri for onto in world.ontologies.values() if onto.namespace and (ns_iri := onto.namespace.base_iri) in relevant_namespace_iris)
    for entity_type in [world.classes, world.object_properties, world.data_properties, world.individuals]:
        for entity in entity_type():
            if entity.namespace and (ns_iri := entity.namespace.base_iri) in relevant_namespace_iris:
                detected_ns.add(ns_iri)
    if detected_ns:
        for ns_iri in sorted(list(detected_ns)): print(f"    - {ns_iri}")
    else: print("    - No namespaces from entities matching 'relevant_namespace_iris' were found.")
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
            named_superclasses = [f"{(s.namespace.name + ':') if s.namespace != owl and s.namespace != (current_onto.namespace if current_onto else None) and hasattr(s.namespace, 'name') and s.namespace.name else ''}{s.name}" for s in cls.is_a if isinstance(s, ThingClass) and not (isinstance(s, (owlready2.class_construct.Restriction, owlready2.class_construct.LogicalClassConstruct)) or (hasattr(s, 'one_of') and s.one_of) or isinstance(s, owlready2.prop.PropertyClass))]
            other_super_constructs = [str(s) for s in cls.is_a if not isinstance(s, ThingClass) and s != owl.Thing]
            if named_superclasses: print(f"    Direct Named Superclasses: {', '.join(named_superclasses)}")
            if other_super_constructs: print(f"    Other Superclass Expressions (is_a): {', '.join(other_super_constructs)}")
            equivalent_definitions = [f"{(eq.namespace.name + ':') if eq.namespace != owl and eq.namespace != (current_onto.namespace if current_onto else None) and hasattr(eq.namespace, 'name') and eq.namespace.name else ''}{eq.name}" if isinstance(eq, ThingClass) and not (isinstance(eq, (owlready2.class_construct.Restriction, owlready2.class_construct.LogicalClassConstruct)) or (hasattr(eq, 'one_of') and eq.one_of) or isinstance(eq, owlready2.prop.PropertyClass)) else str(eq) for eq in cls.equivalent_to]
            if equivalent_definitions: print(f"    Equivalent to: {', '.join(equivalent_definitions)}")
            disjoint_axioms_logged = False
            for disjoint_statement in cls.disjoints(): 
                direct_disjoints = [e.name for e in disjoint_statement.entities if e != cls]
                if direct_disjoints:
                    if not disjoint_axioms_logged: print(f"    Disjoint With:"); disjoint_axioms_logged = True
                    print(f"      - Axiom implies disjoint with: {', '.join(direct_disjoints)}")
    if not classes_found: print("  No user-defined Classes found in the relevant namespaces.")
    print("\n--- End of Class Definitions ---")

def log_property_definitions(world, current_onto, relevant_namespace_iris):
    for prop_type_name, prop_iterator, top_prop in [
        ("Object Property", world.object_properties, owl.topObjectProperty),
        ("Data Property", world.data_properties, owl.topDataProperty)
    ]:
        print(f"\n--- {prop_type_name} Definitions from Relevant Namespaces in Ontology: {current_onto.name if current_onto else 'N/A'} ---")
        properties_found = False
        for p in prop_iterator():
            if p.namespace and p.namespace.base_iri in relevant_namespace_iris:
                properties_found = True
                print(f"\n  {prop_type_name}: {p.name} (IRI: {p.iri}, Namespace: {p.namespace.base_iri})")
                if p.label: print(f"    Label: {', '.join(p.label)}")
                if p.comment: print(f"    Comment: {', '.join(p.comment)}")
                if p.domain: print(f"    Domain: {[d.name if hasattr(d, 'name') else str(d) for d in p.domain]}")
                # Corrected line for printing range:
                if p.range: print(f"    Range: {[r.name if hasattr(r, 'name') else str(r) for r in p.range]}")
                characteristics = [str(char).split('.')[-1] for char in p.is_a if isinstance(char, owlready2.prop.PropertyClass) or (isinstance(char, ThingClass) and char.namespace == owl and char != (owl.ObjectProperty if prop_type_name == "Object Property" else owl.DatatypeProperty))]
                if characteristics: print(f"    Characteristics: {characteristics}")
                super_props = [sp.name for sp in p.is_a if isinstance(sp, type(p)) and sp != top_prop and sp != p]
                if super_props: print(f"    Super-properties (direct): {', '.join(super_props)}")
        if not properties_found: print(f"  No {prop_type_name}s found in the relevant namespaces.")
    print("\n--- End of Property Definitions ---")

def check_functional_property_violations(world, relevant_namespace_iris):
    print("\n--- Explicit Functional Property Violation Check (Relevant Namespaces) ---")
    violations_found = False
    for ind in world.individuals():
        if not (hasattr(ind, "namespace") and ind.namespace and ind.namespace.base_iri in relevant_namespace_iris): continue 
        for prop_class_type in [world.object_properties, world.data_properties]:
            for p_class in prop_class_type(): 
                if p_class.namespace and p_class.namespace.base_iri in relevant_namespace_iris and owl.FunctionalProperty in p_class.is_a: 
                    values = p_class[ind] 
                    actual_values = [v for v in (values if isinstance(values, list) else [values]) if v is not None]
                    if len(actual_values) > 1: 
                        violations_found = True
                        value_names = [str(v.name) if hasattr(v, 'name') else str(v) for v in actual_values]
                        print(f"  VIOLATION: Individual '{ind.name}' has >1 value for functional {type(p_class).__name__} '{p_class.name}': {value_names}")
    if not violations_found: print("  No functional property violations explicitly detected from relevant namespaces.")
    print("--- End of Functional Property Check ---")

def log_all_relevant_individual_details_before_reasoning(world, current_onto, relevant_namespace_iris):
    print(f"\n--- Details of All Relevant Individuals (Before Reasoning) ---")
    individuals_found = False
    for ind in world.individuals():
        if not (hasattr(ind, "namespace") and ind.namespace and (ind_ns_iri := ind.namespace.base_iri) in relevant_namespace_iris): continue
        individuals_found = True
        print(f"\n  Individual: {ind.name} (IRI: {ind.iri}, Namespace: {ind_ns_iri})")
        print(f"    Asserted Types (is_a):")
        types_list = list(ind.is_a) 
        if types_list:
            for rdf_type in types_list: print(f"      - {rdf_type.name if hasattr(rdf_type, 'name') else str(rdf_type)} (IRI: {rdf_type.iri}, Namespace: {rdf_type.namespace.base_iri if hasattr(rdf_type, 'namespace') and rdf_type.namespace else 'N/A'})")
        else: print("      - No explicit types (implicitly owl:Thing).")
        if len(types_list) >= 2:
            print("    Disjointness Check Among Asserted Types:")
            disjoint_pairs_found = False
            type_iris_set = {t.iri for t in types_list if isinstance(t, ThingClass)}
            processed_pairs = set()
            for i in range(len(types_list)):
                type1 = types_list[i]
                if not isinstance(type1, ThingClass): continue
                for j in range(i + 1, len(types_list)):
                    type2 = types_list[j]
                    if not isinstance(type2, ThingClass): continue
                    pair_key = tuple(sorted((type1.iri, type2.iri)))
                    if pair_key in processed_pairs: continue
                    processed_pairs.add(pair_key)
                    for disjoint_axiom in type1.disjoints(): 
                        if type2 in disjoint_axiom.entities:
                            print(f"      - Types '{type1.name}' and '{type2.name}' are declared disjoint."); disjoint_pairs_found = True; break 
                    if disjoint_pairs_found and any(type1.iri == t.iri and type2.iri == t2.iri for t,t2 in processed_pairs if t.iri < t2.iri): break # Already reported this pair via type1
            if not disjoint_pairs_found: print("      - No asserted type pairs are explicitly declared disjoint by owl:disjointWith.")
    if not individuals_found: print("  No individuals found in relevant namespaces to log before reasoning.")
    print(f"--- End of Details of All Relevant Individuals (Before Reasoning) ---")

def log_explicit_instance_consistency_check(world, current_onto, relevant_namespace_iris):
    print("\n--- Instance Details & Consistency Check (Relevant Namespaces, After Reasoning) ---")
    instances_found_in_relevant_namespaces = False; any_inconsistency_found_in_instances = False
    nothing_individuals_set = set(owl.Nothing.instances(world=world))
    print(f"  DEBUG: Individuals inferred as owl.Nothing by reasoner: {[i.name for i in nothing_individuals_set if hasattr(i, 'name')] or 'None'}")
    for ind in world.individuals():
        if not (hasattr(ind, "namespace") and ind.namespace and (ind_ns_iri := ind.namespace.base_iri) in relevant_namespace_iris): continue
        instances_found_in_relevant_namespaces = True
        print(f"\n  Instance: {ind.name} (IRI: {ind.iri}, Namespace: {ind_ns_iri})")
        if ind.label: print(f"    Label: {', '.join(ind.label)}")
        if ind.comment: print(f"    Comment: {', '.join(ind.comment)}")
        direct_types_str = []
        is_inconsistent_instance = ind in nothing_individuals_set
        for rdf_type in ind.is_a: 
            type_name = rdf_type.name if hasattr(rdf_type, 'name') else str(rdf_type)
            ns_prefix = ""
            if hasattr(rdf_type, 'namespace') and rdf_type.namespace != owl and not (current_onto and current_onto.namespace and rdf_type.namespace.base_iri == current_onto.namespace.base_iri):
                if rdf_type.namespace.name and rdf_type.namespace.name != "owl": ns_prefix = f"{rdf_type.namespace.name}:"
            direct_types_str.append(f"{ns_prefix}{type_name}")
        print(f"    Types (After Reasoning): {', '.join(direct_types_str) if direct_types_str else 'None (implicitly owl:Thing)'}")
        print(f"    Properties:")
        has_any_property = False
        for prop_list_func in [world.object_properties, world.data_properties]:
            for p in prop_list_func():
                try: values = p[ind]
                except Exception: values = []
                if values:
                    has_any_property = True
                    actual_values = values if isinstance(values, list) else [values]
                    value_strs = []
                    for value in actual_values:
                        if value is None: continue
                        if isinstance(value, owlready2.entity.Thing):
                            val_ns_prefix = ""
                            if hasattr(value, 'namespace') and value.namespace != owl and not (current_onto and current_onto.namespace and value.namespace.base_iri == current_onto.namespace.base_iri):
                                if value.namespace.name and value.namespace.name != "owl": val_ns_prefix = f"{value.namespace.name}:"
                            value_strs.append(f"{val_ns_prefix}{value.name} (IRI: {value.iri})")
                        elif isinstance(value, datetime): value_strs.append(f'"{value.isoformat()}"^^xsd:dateTime')
                        elif isinstance(value, bool): value_strs.append(f'"{str(value).lower()}"^^xsd:boolean')
                        elif isinstance(value, (int, float)): value_strs.append(f'"{str(value)}"^{"xsd:integer" if isinstance(value, int) else "xsd:decimal"}')
                        else: value_strs.append(f'"{str(value)}"')
                    if value_strs: print(f"      - {p.name}: {', '.join(value_strs)}")
        if not has_any_property: print("      - No asserted object or data properties found.")
        if is_inconsistent_instance: any_inconsistency_found_in_instances = True; print(f"    🔴 INCONSISTENT INSTANCE: This instance ({ind.name}) is inferred to be an instance of owl.Nothing.")
        print("-" * 10) 
    if not instances_found_in_relevant_namespaces: print("  No individuals found in the specified relevant namespaces.")
    if any_inconsistency_found_in_instances: print("\n  Overall Instance Consistency (Relevant Namespaces): At least one instance from relevant namespaces is inconsistent.")
    elif instances_found_in_relevant_namespaces: print("\n  Overall Instance Consistency (Relevant Namespaces): All checked instances from relevant namespaces appear consistent.")
    print("--- End of Instance Details & Consistency Check (After Reasoning) ---")
    return any_inconsistency_found_in_instances 

def run_minimal_consistency_test():
    print("\n--- Running Minimal In-Script Consistency Test ---")
    temp_world = World(filename = ":memory:") 
    minimal_test_hermit_reported_inconsistency = False 
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
            hermit_command_minimal = ""
            temp_file_path_minimal = ""
            try:
                fd, temp_file_path_minimal = tempfile.mkstemp(suffix=".owl", prefix="owlready_hermit_minimal_")
                os.close(fd)
                temp_onto.save(file=temp_file_path_minimal, format="rdfxml")
                
                hermit_jar_path_val = owlready2.reasoning.HERMIT_JAR 
                hermit_dir_path_val = os.path.dirname(hermit_jar_path_val)
                cp = "%s%s%s" % (hermit_dir_path_val, os.pathsep, hermit_jar_path_val)
                
                command = [owlready2.JAVA_EXE] + owlready2.reasoning.JAVA_OPTIONS + ["-cp", cp, "org.semanticweb.HermiT.cli.CommandLine", "-c", "-O", "-D", "-I", "file:///%s" % temp_file_path_minimal.replace(os.sep, '/'), "-Y"]
                hermit_command_minimal = " ".join(shlex.quote(s) for s in command) 
                
                print(f"    * Owlready2 (Minimal Test) * Running HermiT with command:")
                print(f"      {hermit_command_minimal}")
                print(f"    * Owlready2 (Minimal Test) * Using temporary file: {temp_file_path_minimal}")
                print(f"    >>> ACTION (Minimal Test): If this test fails with a Java error, try running the above HermiT command manually in your terminal using the specified temporary file.")
                
                sync_reasoner_hermit(temp_world, infer_property_values=False, debug=1) 
                if test_individual in owl.Nothing.instances(world=temp_world):
                    print(f"    SUCCESS (Minimal Test): Individual '{test_individual.name}' IS an instance of owl.Nothing after reasoning.")
                    minimal_test_hermit_reported_inconsistency = True
                else:
                    print(f"    FAILURE (Minimal Test): Individual '{test_individual.name}' IS NOT an instance of owl.Nothing after reasoning completed (HermiT exited 0).")
            except subprocess.CalledProcessError as e_minimal_sub:
                print(f"    ERROR (Minimal Test): HermiT subprocess failed with exit code {e_minimal_sub.returncode}.")
                if e_minimal_sub.output: print(f"      HermiT output (stderr/stdout):\n{e_minimal_sub.output.decode(errors='replace')}")
                if e_minimal_sub.returncode == 1: 
                    print(f"    NOTE (Minimal Test): HermiT exited with status 1, which usually indicates an inconsistency was found.")
                    minimal_test_hermit_reported_inconsistency = True 
            except OwlReadyInconsistentOntologyError: 
                print(f"    SUCCESS (Minimal Test - OwlReadyInconsistentOntologyError): Owlready2 reported that HermiT found the ontology inconsistent.")
                if test_individual in owl.Nothing.instances(world=temp_world): # Check after exception
                    print(f"      Confirmed: Individual '{test_individual.name}' IS an instance of owl.Nothing.")
                minimal_test_hermit_reported_inconsistency = True 
            except Exception as e_minimal:
                print(f"    ERROR during minimal test reasoning: {e_minimal}")
                traceback.print_exc(file=sys.stdout)
            finally:
                if temp_file_path_minimal and os.path.exists(temp_file_path_minimal) and not owlready2.reasoning.KEEP_TMP_FILES:
                    try: os.remove(temp_file_path_minimal)
                    except Exception as e_rm_tmp: print(f"    Warning: Could not remove minimal test temporary file {temp_file_path_minimal}: {e_rm_tmp}")
                elif temp_file_path_minimal and os.path.exists(temp_file_path_minimal):
                     print(f"    Minimal test temporary file kept at: {temp_file_path_minimal}")
    print(f"--- End of Minimal In-Script Consistency Test (Overall Result: {'SUCCESS' if minimal_test_hermit_reported_inconsistency else 'FAILURE/UNKNOWN'}) ---")
    return minimal_test_hermit_reported_inconsistency


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
            
            minimal_test_passed = run_minimal_consistency_test()
            if not minimal_test_passed:
                print("\nCRITICAL: The minimal consistency test FAILED to confirm HermiT's inconsistency detection.")
                print("          This indicates a fundamental problem with the Java/HermiT setup or its interaction with Owlready2.")
                print("          Please resolve this before checking the main ontology. Check HermiT's manual run output for the minimal test.")

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
            main_hermit_temp_file_path = None 
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
                
                hermit_jar_path_main_val = owlready2.reasoning.HERMIT_JAR
                hermit_dir_path_main_val = os.path.dirname(hermit_jar_path_main_val)
                cp_main = "%s%s%s" % (hermit_dir_path_main_val, os.pathsep, hermit_jar_path_main_val)
                
                generic_command_main_str = f"'{owlready2.JAVA_EXE}' {' '.join(owlready2.reasoning.JAVA_OPTIONS)} -cp '{cp_main}' org.semanticweb.HermiT.cli.CommandLine -c -O -D -I file:///PATH_TO_TEMP_OWL_FILE -Y"
                print(f"    * Owlready2 (Main Ontology) * Will attempt to run HermiT with a command similar to:")
                print(f"      {generic_command_main_str}")
                print(f"    >>> ACTION (Main Ontology): If reasoning fails, check HermiT's output (with debug=1) for the actual temp file path and run manually.")

                with world: 
                    sync_reasoner_hermit(world, infer_property_values=True, debug=1) 

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
                    # ... (notes remain the same)
                    return False
            except owlready2.base.OwlReadyInconsistentOntologyError as e:
                print(f"\n❌ MAIN ONTOLOGY IS GLOBALLY INCONSISTENT (OwlReadyInconsistentOntologyError raised by Owlready2):")
                error_message = str(e)
                print(f"  Error details from Owlready2: {error_message}")
                hermit_output_in_message = "org.semanticweb.HermiT" in error_message or "InconsistentOntologyException" in error_message
                
                if hasattr(e, 'reasoner_output') and e.reasoner_output and not hermit_output_in_message:
                    print(f"  Explicitly printing e.reasoner_output:\n<<<<<<<<<< REASONER OUTPUT START >>>>>>>>>>\n{e.reasoner_output}\n<<<<<<<<<< REASONER OUTPUT END >>>>>>>>>>")
                elif not hasattr(e, 'reasoner_output') or not e.reasoner_output:
                    print(f"  e.reasoner_output was not available or empty.")

                print(f"  This error (often due to HermiT exiting with status 1) typically means HermiT FOUND THE ONTOLOGY INCONSISTENT.")
                print(f"  Your manual execution confirmed: org.semanticweb.owlapi.reasoner.InconsistentOntologyException.")
                print(f"  The script's 'Owlready2 Internal Pre-Reasoner Inconsistency Check' likely identified a cause (e.g., ConflictingEntity_001).")
                print(f"  The Python 'world' may not be fully updated with all consequences (like specific individuals being owl:Nothing) after this type of error.")
                print(f"  >>> ACTION: Fix the inconsistencies identified (e.g., ConflictingEntity_001) in your GSMFO.owl file.")
                print(f"  Full Python traceback for this OwlReadyInconsistentOntologyError:")
                traceback.print_exc() 
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
        if not owlready2.JAVA_EXE: 
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
