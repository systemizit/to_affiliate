# -*- coding: utf-8 -*-


def migrate(env, version):
    """
    drop config table
    """
    env.execute("""    
        DELETE FROM ir_model_data WHERE model='affiliate.config.settings';
        
        DELETE FROM ir_model_fields WHERE id IN (
            select f.id from ir_model_fields as f
            join ir_model as m ON m.id = f.model_id
            where m.model='affiliate.config.settings'
        );
            
        DROP TABLE IF EXISTS affiliate_config_settings;        
    """)    

