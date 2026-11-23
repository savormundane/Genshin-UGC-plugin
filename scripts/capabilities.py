"""Actual execution prerequisites and source-bound capability evidence."""
import importlib.util,importlib.metadata,json,shutil,sys,subprocess
from authoring_io import *
from runtime_policy import REQUIREMENTS,supported_python
from validation_evidence import execution_inventory,validation_dependencies,backend_inventory,case_coverage
CAPABILITIES={
 'knowledge':('knowledge.py','knowledge-reliability.md'),'diagnosis':('project_diagnosis.py','project-diagnosis.md'),'asset_inspection':('asset_inspection.py','asset-inspection.md'),
 'mcp':('mcp_service.py','local-mcp.md'), 'asset_batch':('asset_batch.py','asset-generation.md'),
 'native':('native_core.py','native-maintenance.md'), 'storage':('storage_authoring.py','storage-authoring.md'),
 'protocol':('protocol_codegen.py','protocol-v2.md'), 'ui':('runtime_ui.lua','runtime-ui.md'),
 'assembly':('client_assembly.py','client-assembly.md'), 'simulation':('joint_simulator.py','joint-simulation.md'),
 'algorithms':('runtime_algorithms.lua','algorithms-experiments.md'), 'asset_fit':('asset_fit.py','asset-fit.md'),
 'native_assets':('native_assets.py','native-assets.md'),
 'production':('production_v2.py','production-v2.md'),'platform':('platform_profiles.py','platform-profiles.md'),
 'project':('project_index.py','project-index.md'),'native_changes':('native_changes.py','native-changes.md'),
 'scene':('scene_authoring.py','native-scene.md')}
SUPPORT={
 'knowledge':{'operations':['api_lookup','source_integrity','declared_derived_unknown','conflict_notes','versioned_document_selection'],'authority':'bundled document provenance; no inferred host success'},
 'diagnosis':{'operations':['explicit_readonly_checks','JSON_or_text_report','artifact_bound_manual_records','AST_update_cost_hints'],'performance':'risk indications, not device measurement'},
 'asset_inspection':{'operations':['check','diff','RGBA_statistics','rectangle_reconstruction','text_cost_statistics'],'formats':['image','shape_schema1','genshin-ugc-assets_schema1'],'host_rendering':'not_checked'},
 'asset_batch':{'operations':['preview','generate','weighted_shared_control_budget','produce'],'host_rendering':'not_checked'},
 'mcp':{'operations':['doctor','capabilities','docs_search','nodes_lookup','graph_check','resources_lookup','native_inspect','native_audit','project_inspect','client_check','produce','native_apply','native_diff','native_plan','simulate','experiment_run','experiment_compare','logs_diagnose','verify','api_lookup','diagnose'],
        'transport':'local_stdio','sdk':'mcp==2.3.0','runtime_control':False,'trusted_project_sources_required':True},
 'scene':{'operations':['native_model_catalogue','static_gia','place_static_scene','duplicate_entities','arrange_instances','create_object_templates','instantiate_object_templates','place_model_instances',
                        'add_scene_points','add_respawn_points','add_native_movers','set_native_preset_state','add_point_light','inspect','scene_scope','set_entity_transform','whitebox_preview','export_whitebox','gil_plan_apply','produce'],
          'static_gia_target':{'version':'7.2','mode':'beyond'},'editor':'not_checked','host':'not_checked'},
 'native_changes':{'operations':['diff','plan','apply_plan','source_content_binding','expected_result_binding','protected_bytes','produce','portable'],'diff_formats':['gil','gia'],'plan_baseline':'gil','complete_semantic_diff':False,'scope':'calibrated objects/references/ports and complete top-level byte change detection'},
 'project':{'operations':['inspect','scene_scope','check','direct_consumers','transitive_consumers','required_references','custom_variable_declarations','graph_variable_declarations_and_defaults','static_graph_variable_accesses','variable_inheritance_and_structure_references','final_production_check','portable_artifacts'],'scope':'calibrated native and client object references','complete_reference_index':False,'unindexed':['arbitrary_component_payloads','custom_variable_access_and_literal_targets','graph_variable_dynamic_access_and_overrides','implicit_graph_structure_identity','untyped_numeric_constants','dynamic_Lua_identifiers','platform_resource_catalogue']},
 'platform':{'operations':['docs_search','docs_show','docs_diff','profile','configuration_check','selected_native_timer_binding','final_timer_constant_readback','set_timer_sequence','disturbance_semantics','push_collision_prerequisites','filter_semantics','camera_takeover_restore','velocity_force_distinction','declared_translation_coverage','zero_arrival_radius'],'modes':['classic','beyond'],'scope':'declared_configuration','native_artifact_verified':False},
 'native':{'operations':['inspect','audit','append_graph','replace_graph','rewire','mount_instance','mount_template','section_from','optimize_read_expression','set_custom_variable_default','set_timer_sequence','set_object_transform','set_entity_transform','set_decoration','append_decorations','add_box_trigger','set_linear_motion',
                       'place_static_scene','duplicate_entities','arrange_instances','add_scene_points','set_scene_camera','set_scene_point','set_terrain_cells','set_fixed_environment_hour','set_point_light',
                       'set_native_class','native_skill','native_creature_graph','set_creature_skill_set','native_combat','native_unit_status','set_native_faction_relations','add_native_variables',
                       'set_native_player_group','add_respawn_points','set_native_revive','economy_config','native_economy_binding','create_native_drop','add_native_global_timer','native_hud','set_native_hud_control','append_client_ui'],
           'gameplay_guide':'native-gameplay.md','graph_kinds':['ordinary','composite'],'guard':['base_sha256','unique_target','allowed_fields','protected_bytes','types','struct_identity','structure_declarations_and_defaults','dictionary_structure_references_and_defaults','custom_variable_declarations_and_defaults','graph_variable_declarations_and_defaults','static_graph_variable_accesses','storage_slot_references','dynamic_ports','flow_and_data_port_contracts','versions','mount_library','declaration_signature_references','composite_interfaces','GIA_dependencies','GIA_signal_roles_and_descriptors','GIA_signal_compilation_readback','composite_compilation_readback'],'composite_kernel_indices':'equal ordinals and calibrated structure update mappings','composite_execution':'not_implemented','optimizer_default':'disabled'},
 'storage':{'schema':[2,3],'fields':['integer','boolean','integer_list'],'operations':['native_declarations','slots','signals','Graph_Code','client_adapter','server_transport','read','write','readback','retry','exit_intent','record_version_guard','explicit_QX_migration_chain','migration_candidate_readback','schema3_migration_ticket_commit','logical_capacity_guard','codec','append_dictionary','achievement_request_and_confirmation','diagnose'],'schema3_operations':['open_session','expected_revision_guard','stale_session_guard','exact_duplicate_idempotency','stored_capacity_guard','session_slot_log_correlation','compatible_record_version_upgrade'],'host_quota':'not_checked'},
 'protocol':{'operations':['native_definitions','Lua_bridge','typed_readback','ordered_contiguous','snapshot_monotonic','revision','confirmation_set','roster_snapshot','barrier','checkpoint','session_isolation','membership_revision','withdraw_revision','validated_checkpoint_restore','final_client_direction_contract','final_native_protocol_layout'],'arbitrary_struct_transport':False},
 'ui':{'operations':['identity_pool','property_cache','cancel_queue','create_and_write_budget','foreground_priority','position_owner','drag_cancel','listener_scope','overlay_restore','pause_clock','keyed_list','native_fixed_anchor_layout','native_positive_xy_scale','final_layout_readback','final_parent_local_size_check'],'rendering':'host_required'},
 'assembly':{'operations':['ordered_manifest','dependency_check','local_module_inline','per_file_digest','line_map','embedded_source_check','final_lua53_compilation','all_embedded_mappings','digest_bound_syntax_diagnostics','contract_bound_lexical_API_check','declaration_type_bindings','bound_integer_literals','final_control_template_references','readonly_literal_table_fields','explicit_client_variable_owner_contract','custom_variable_inheritance_check'],'host_require_required':False,'api_and_reference_crosscheck':False,'api_scope':'lexical host members, permissions, call convention, arity and resolved types; dynamic containers and engineering references incomplete'},
 'simulation':{'optional_external_backend':{'entry':'beyond','commit':'02a5ea2cd38bb5bcf7a7ce6dd745be3bb1ae655c','dependency':'bundled Windows x64 runtime; Node 22+','gil_controls':['container','text','area','button'],'rendering':'software PNG','production_binding':'@level final GIL and SHA256','portable':'bundled backend input closure and isolated rebuild','evidence':'not_checked','native_equivalence':False},
               'operations':['independent_Lua_clients','final_GIL_graph_read','deterministic_queue','delay','drop','duplicate','reorder','failure_trace','failure_replay','network_timer_deadline_clock','required_timer_event_acceptance','bidirectional_serialized_data_edges','explicit_client_variable_snapshots','client_variable_listener_cleanup','native_only_mounted_graphs','model_visibility_assertions','world_position_observations','local_template_mounts','entity_variable_assertions'],
               'native_nodes':['signal_event','server_signal_broadcast','targeted_signal_send','custom_variable_read_write','list_assembly_index_length','container_reference_read_write','list_clear_insert_remove_modify_concatenate','custom_variable_change_event','receiver_sender_and_GUID_identity','structure_assembly_split','local_variable','branch','multiple_branches','finite_loop_inclusive_with_break','comparison','arithmetic_add_subtract_multiply','logical_boolean','print','achievement_tally_query','start_pause_resume_stop_timer','entity_timer_event','explicit_entity_creation_event','level_scoped_entity_removal','removed_entity_timer_listener_cleanup','activate_disable_model_display','uniform_basic_linear_motion'],
               'timer_scope':'entity-local sequences and explicit index base','motion_scope':'one active world-space uniform linear motion per dynamic placed entity','unknown_node':'fails_when_executed','persistence':'explicit_settlement_copy_model'},
 'algorithms':{'operations':['independent_rng_restore','stable_heap','Dijkstra','grid4','geometry_query','reservation_expiry','state_machine','pause_clock','event_replay','LRU','development_holdout','paired_compare','failure_trace'],'policy_and_score':'project_supplied'},
 'asset_fit':{'entry':'assets fit','schemas':[1,2],'schema2_algorithm':'residual-budget-2','delivery_budget':'per-layer and batch rectangle limits; not a platform limit','shapes':['circle','ellipse','axis_aligned_line','rect'],'error':'premultiplied RGBA MSE','operations':['seeded_progressive_fit','regional_refinement','digest_bound_resume','layer_batch','lossless_rectangle_lowering','Lua','calibrated_rectangle_GIA'],'editor':'not_checked','host':'not_checked'},
 'native_assets':{'projection':'xy_x90','template_id':10009001,'operations':['dependencies','position_rotation_scale_color','single_depth_layer','explicit_depth_layers','alpha_composited_software_preview','anchor','lossless_grid_merge','JSON_Lua_preview_catalogue','bounded_LRU','weighted_rectangle_cache','identity_asset_leases','explicit_catalogue_loader'],'unsupported':'reject'},
 'production':{'schema':[1,2],'operations':['produce','atomic_output','active_gil_baseline','typed_native_bindings','rebase_native_bindings','summary','final_audit','declared_models_experiments','dependency_manifest','independent_rebuild','artifact_byte_compare','artifact_role_comparison','portable_input_closure','portable_rebuild','impact_selection','doctor','capabilities'],'portable':'explicit production portable configuration; recorded Python/Node/package dependencies required','editor_host':'not_checked'}}
CAPABILITY_GROUPS = {
    'entrypoints': (
        'plugin.json', '.codex-plugin/plugin.json', 'mcp.json',
        'pyproject.toml', 'uv.lock', 'scripts/runtime_policy.py',
        'scripts/qianxing.py', 'scripts/mcp_launcher.cjs', 'scripts/mcp_service.py', 'scripts/mcp_bridge.py',
        'scripts/mcp_worker.py', 'scripts/capability_index.py', 'scripts/capability-layers.json', 'scripts/capabilities.py',
    ),
    'editor': (
        'scripts/platform-sources.json', 'scripts/platform_profiles.py', 'scripts/platform_rules72.py',
        'scripts/platform_schema.py', 'scripts/platform_native.py', 'scripts/project_index.py',
        'scripts/native_gameplay_index.py', 'scripts/native_scene.py', 'scripts/native_scene_edits.py',
        'scripts/native_scene_settings.py',
    ),
    'graph': (
        'scripts/node_build.py', 'scripts/graph_validation.py', 'scripts/graph_resources.py',
        'scripts/native_bindings.py', 'scripts/native_build.py', 'scripts/protocol_codegen.py',
        'scripts/native_model.py', 'scripts/native_timers.py', 'vendor/ayaya/VENDORED.json',
    ),
    'client': (
        'scripts/knowledge-sources.json', 'scripts/knowledge.py', 'scripts/client_api_catalogue.py',
        'scripts/client_api.py', 'scripts/client_ast.cjs', 'scripts/client_check.py', 'scripts/client_references.py',
        'scripts/client_assembly.py', 'scripts/client_variables.py', 'scripts/client_signal_binding.py',
        'skills/qianxing-editor/references/client-controls-api.md', 'scripts/client_simulator.py',
        'scripts/client_simulator.lua', 'scripts/joint_simulator.py', 'scripts/beyond_backend.py',
        'scripts/beyond_gil.py', 'scripts/beyond_worker.mjs', 'vendor/beyond/bundle.json',
    ),
    'gil': (
        'scripts/level_inventory.py', 'scripts/level_authoring.py', 'scripts/native_core.py', 'scripts/native_changes.py',
        'scripts/native_ports.py', 'scripts/native-client-ports.json', 'scripts/native_resources.py', 'scripts/native_signals.py',
        'scripts/native_structures.py', 'scripts/native_variables.py', 'scripts/native_prefabs.py', 'scripts/native_gameplay.py',
        'scripts/native_economy.py', 'scripts/native_hud.py', 'scripts/native_client_ui.py', 'scripts/native_gia.py', 'scripts/storage_authoring.py',
        'scripts/storage_v3.py', 'scripts/authoring_io.py', 'scripts/production_core.py', 'scripts/production_v2.py',
        'scripts/delivery_verify.py', 'scripts/portable_trust.py', 'scripts/portable_delivery.py',
    ),
    'assets': (
        'scripts/resource_catalogue.py', 'scripts/scene-model-candidates.json', 'scripts/scene_authoring.py',
        'scripts/asset_pipeline.py', 'scripts/asset_batch.py', 'scripts/asset_core.py', 'scripts/asset_inspection.py',
        'scripts/asset_fit.py', 'scripts/asset_fit_v2.py', 'scripts/native_assets.py',
    ),
}


def capability_snapshot(legacy_files, compare):
    names=set(legacy_files).union(*CAPABILITY_GROUPS.values())
    current={name:sha_file(PLUGIN/name) if (PLUGIN/name).is_file() else None for name in sorted(names)}
    legacy=sha(canonical({name:current[name] for name in legacy_files}).encode('utf-8'))
    groups={key:{'sha256':sha(canonical({name:current[name] for name in files}).encode('utf-8')),
                 'file_count':len(files),'missing':[name for name in files if current[name] is None]}
            for key,files in CAPABILITY_GROUPS.items()}
    result={'path':str(PLUGIN),'version':read_json(PLUGIN/'plugin.json')['version'],'capability_sha256':legacy,
            'fingerprint_files':list(legacy_files),'capability_groups':groups}
    if compare is not None:
        target=Path(compare).resolve()
        if not target.is_dir():
            raise ValueError('Compare path must be a plugin directory')
        other={name:sha_file(target/name) if (target/name).is_file() else None for name in current}
        differences={}
        for group,files in CAPABILITY_GROUPS.items():
            changed=[{'file':name,'current_sha256':current[name],'compare_sha256':other[name]} for name in files
                     if current[name]!=other[name] and current[name] is not None and other[name] is not None]
            missing_current=[name for name in files if current[name] is None]
            missing_compare=[name for name in files if other[name] is None]
            differences[group]={'status':'different' if changed or missing_current or missing_compare else 'same',
                                'changes':changed,'missing_current':missing_current,'missing_compare':missing_compare}
        result['comparison']={'path':str(target),'version':read_json(target/'plugin.json').get('version') if other['plugin.json'] else None,
                              'status':'different' if any(group['status']=='different' for group in differences.values()) else 'same',
                              'groups':differences}
    return result


def doctor(compare=None):
    node=shutil.which('node');node_version=None
    if node:
        probe=subprocess.run([node,'--version'],capture_output=True,text=True)
        if probe.returncode==0:node_version=probe.stdout.strip()
    versions={d.metadata['Name'].lower():d.version for d in importlib.metadata.distributions() if d.metadata['Name']}
    dependencies={name:{'required':required,'installed':versions.get(name),'status':'not_checked' if name not in versions else 'passed' if versions[name]==required else 'failed'} for name,required in REQUIREMENTS.items()}
    imports=subprocess.run([sys.executable,'-B','-c','import mcp,lupa.lua53,PIL'],capture_output=True,text=True)
    supported=sys.implementation.name=='cpython' and supported_python(sys.version_info)
    node_supported=bool(node_version and node_version.lstrip('v').split('.')[0].isdigit() and int(node_version.lstrip('v').split('.')[0])>=22)
    status='failed' if not supported or not node_supported or imports.returncode or any(r['status']=='failed' for r in dependencies.values()) else 'not_checked' if any(r['status']=='not_checked' for r in dependencies.values()) else 'passed'
    fingerprint_files = (
        'plugin.json', 'mcp.json', '.codex-plugin/plugin.json', 'scripts/qianxing.py',
        'scripts/mcp_launcher.cjs', 'scripts/mcp_service.py', 'scripts/mcp_bridge.py',
        'scripts/mcp_worker.py', 'scripts/capability_index.py', 'scripts/capabilities.py',
        'scripts/project_index.py', 'scripts/native_gameplay_index.py', 'scripts/native_bindings.py', 'scripts/authoring_io.py',
        'scripts/native_core.py', 'scripts/native_changes.py', 'scripts/native_ports.py',
        'scripts/native-client-ports.json', 'scripts/native_resources.py', 'scripts/native_signals.py', 'scripts/native_structures.py',
        'scripts/native_scene.py', 'scripts/native_scene_edits.py', 'scripts/native_scene_settings.py', 'scripts/level_inventory.py',
        'scripts/native_prefabs.py', 'scripts/native_gameplay.py', 'scripts/native_economy.py', 'scripts/native_hud.py',
        'scripts/native_gia.py', 'scripts/storage_authoring.py', 'scripts/storage_v3.py',
        'scripts/asset_pipeline.py', 'scripts/asset_core.py', 'scripts/asset_fit.py', 'scripts/asset_fit_v2.py',
        'scripts/client_check.py', 'scripts/client_simulator.py', 'scripts/client_simulator.lua',
        'scripts/joint_simulator.py', 'scripts/native_model.py', 'scripts/native_timers.py', 'scripts/beyond_gil.py',
        'scripts/beyond_backend.py', 'scripts/beyond_worker.mjs', 'scripts/node_build.py', 'scripts/graph_validation.py',
        'scripts/native_build.py', 'scripts/production_core.py', 'scripts/production_v2.py',
        'vendor/ayaya/VENDORED.json', 'vendor/beyond/bundle.json',
    )
    return {'schema':2,'status':status,
            'plugin':capability_snapshot(fingerprint_files,compare),
            'python':sys.version.split()[0],'python_executable':sys.executable,'python_supported':supported,'node':node,'node_version':node_version,'node_supported':node_supported,
            'dependencies':dependencies,'dependency_imports':{'status':'passed' if imports.returncode==0 else 'failed','error':imports.stderr[-1500:] if imports.returncode else None},
            'pillow':importlib.util.find_spec('PIL')is not None,'lua53':importlib.util.find_spec('lupa')is not None and importlib.util.find_spec('lupa.lua53')is not None,
            'ayaya':(PLUGIN/'vendor/ayaya/private_extensions/run_ugc_file_tools.py').is_file(),'beyond':{'bundled':(PLUGIN/'vendor/beyond/bundle.json').is_file(),'platform':'Windows x64','requires':'Node 22+','integrity':'checked_on_run','runtime':'not_checked'},'mcp_host_loading':'not_checked','global_configuration_changed':False}
def capabilities(evidence=None,tests_root=None,platform=None,mode=None):
    proof=read_json(evidence)if evidence else None
    current=inventory(PLUGIN/'scripts');verified=False
    problems=[]
    if proof:
        test_directory=Path(tests_root)if tests_root else PLUGIN.parent.parent/'development'
        if proof.get('schema')!=3:problems.append('validation evidence schema 3 required')
        if proof.get('validation_dependencies')!=validation_dependencies(test_directory):problems.append('validation helpers, fixtures or rules changed')
        if proof.get('backends')!=backend_inventory():problems.append('execution backend changed or unavailable')
        if proof.get('structural_files')!=inventory(PLUGIN):problems.append('structural validation inputs changed')
        structural=Path(evidence).parent/'source-validation.json'
        if not structural.is_file()or sha(structural.read_bytes())!=proof.get('structural_sha256'):
            problems.append('structural evidence missing or changed')
        elif read_json(structural).get('checks_passed')is not True:problems.append('structural validation did not pass')
        selected=proof.get('selected',[]);results=proof.get('results',[])
        names=[r.get('test')for r in results]
        if not selected or len(selected)!=len(set(selected))or len(names)!=len(set(names))or set(names)!=set(selected):problems.append('test selection/results mismatch or empty')
        if proof.get('source_unchanged')is not True:problems.append('source changed during validation or guard absent')
        if proof.get('scope')!='self-use':problems.append('evidence scope is not self-use')
        for r in results:
            name=r.get('test','')
            if not isinstance(name,str)or Path(name).name!=name or not name.startswith('test_')or not name.endswith('.py'):
                problems.append('invalid test identity');continue
            p=test_directory/name
            if not p.is_file()or sha(p.read_bytes())!=r.get('test_sha256'):problems.append('test missing or changed: '+name)
            if r.get('passed')is not True or r.get('exit_code')!=0:problems.append('test did not pass: '+name)
            cases=r.get('cases',[]);ids=[c.get('id')for c in cases]
            if not cases or len(ids)!=len(set(ids))or any(c.get('status')!='passed'for c in cases):problems.append('test cases missing, duplicated, skipped or failed: '+name)
            case_path=Path(evidence).parent/(name+'.cases.json')
            if r.get('case_report')!=case_path.name or not case_path.is_file()or sha(case_path.read_bytes())!=r.get('case_sha256'):
                problems.append('case evidence missing or changed: '+name)
            else:
                actual=read_json(case_path)
                if actual.get('schema')!=1 or actual.get('test')!=name or actual.get('exit_code')!=0 or actual.get('cases')!=cases:problems.append('case evidence disagrees: '+name)
        if proof.get('source_files')!=current or proof.get('execution_files')!=execution_inventory():problems.append('execution source changed')
        if proof.get('passed')is not True:problems.append('validation did not pass')
        verified=not problems
    coverage=case_coverage(proof or{})
    if not verified:
        for item in coverage.values():item['status']='not_checked'
    executed={r['test']for r in(proof or{}).get('results',[])if r.get('passed')}
    required={'scene':{'test_native_scene.py'},'knowledge':{'test_knowledge_diagnosis.py'},'diagnosis':{'test_knowledge_diagnosis.py'},'asset_inspection':{'test_knowledge_diagnosis.py'},'asset_batch':{'test_next_workflows.py'},'mcp':{'test_mcp_service.py'},'native_changes':{'test_native_changes.py','test_native_variables.py','test_native_graph_variables.py'},'project':{'test_project_index.py','test_native_variables.py','test_native_graph_variables.py'},'platform':{'test_platform_profiles.py','test_platform_native.py'},'native':{'test_v3.py','test_v3_integration.py','test_node_build.py','test_v32_regressions.py','test_native_variables.py','test_native_graph_variables.py'},
              'storage':{'test_v3.py','test_v3_integration.py','test_storage_v3.py','test_runtime_migration.py'},
              'asset_fit':{'test_audit_remediation.py','test_asset_fit_v2.py'},
 'native_assets':{'test_v3.py','test_native_asset_layers.py','test_runtime_assets.py'},
              'ui':{'test_v3.py','test_v32_regressions.py','test_native_ui.py','test_native_ui_parent.py'},
              'simulation':{'test_self_use_model.py','test_v3.py','test_v3_integration.py','test_v32_regressions.py','test_storage_v3.py','test_native_timers.py','test_native_ports.py','test_native_lifecycle.py','test_native_removal.py','test_native_event_identity.py','test_joint_variables.py'},
              'protocol':{'test_v3.py','test_v3_integration.py','test_production_integration.py','test_runtime_sessions.py','test_client_protocol.py'},
              'production':{'test_v3.py','test_v3_integration.py','test_production_core.py','test_production_integration.py','test_v32_regressions.py','test_delivery_portable.py'}}
    from capability_layers import describe
    layers=describe(proof,verified)
    from platform_profiles import CATALOGUE,profile
    supported={**SUPPORT,'platform':{**SUPPORT['platform'],'profiles':list(read_json(CATALOGUE)['profiles'])}}
    context=profile(platform,mode)if platform is not None or mode is not None else None
    from capability_index import describe as architecture
    return {'schema':2,'version':read_json(PLUGIN/'plugin.json')['version'],'architecture':architecture(),'platform':context,'platform_version_verified':False,
            'capabilities':{name:{'entry':file,'source_present':(PLUGIN/'scripts'/file).is_file(),'guide':guide,'supported':supported[name],
                                 'layers':layers[name],'offline_evidence':'passed'if verified and required.get(name,{'test_v3.py'})<=executed and coverage[name]['status']=='passed'else'not_checked',
                                 'coverage':coverage[name],'editor':'not_checked','host':'not_checked'}for name,(file,guide)in CAPABILITIES.items()},
            'protocol_types':list(__import__('protocol_types').TYPES),'model':'bounded Lua/API and native graph subset; unsupported operations fail',
            'evidence_current':verified,'evidence_problems':problems,'evidence_file':str(Path(evidence).resolve())if evidence else None,'executed_suites':sorted(executed)if verified else[]}
