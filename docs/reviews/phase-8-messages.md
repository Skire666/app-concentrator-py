# Phase 8 — error messages to read

Every `error.*` message of `assets/i18n/en.json` and `assets/i18n/fr.json`, in catalog order, for the
human reading required by the phase 8 spec ("each one says what happened and what to do").

- Messages marked **revised** were rewritten during phase 8 to add what to do.
- Form messages (timer, favorites, chime, lists, tasks, repetition) state the rule the value breaks: they
  show under the field being typed, so the rule is what to do.
- The four `storage_field_*` messages are lines of the "Data file problem" dialog, prefixed with the field
  name; the dialog intro and its buttons (restore, choose another file, start empty, quit) say what to do.
- `{name}` placeholders are filled when the message is shown.

| Key | English | French | |
|---|---|---|---|
| `unknown` | An unexpected error occurred. The details are on the Journal page. | Une erreur inattendue s'est produite. Les détails sont sur la page Journal. | revised |
| `unset` | An unexpected error occurred. The details are on the Journal page. | Une erreur inattendue s'est produite. Les détails sont sur la page Journal. | revised |
| `required_value_missing` | A value is required. | Une valeur est obligatoire. |  |
| `value_out_of_range` | The value must be between {min} and {max}. | La valeur doit être comprise entre {min} et {max}. |  |
| `text_too_long` | The text must not exceed {max} characters. | Le texte ne doit pas dépasser {max} caractères. |  |
| `format_invalid` | The value does not have the expected format. | La valeur n'a pas le format attendu. |  |
| `entity_not_found` | This item no longer exists: it was deleted in the meantime. | Cet élément n'existe plus : il a été supprimé entre-temps. | revised |
| `entity_duplicate_id` | An item with the same identifier already exists. The details are on the Journal page. | Un élément avec le même identifiant existe déjà. Les détails sont sur la page Journal. | revised |
| `enum_value_unset` | Please choose a value. | Veuillez choisir une valeur. |  |
| `enum_value_unknown` | This value is not recognized by this version of Concentrator. Choose another value. | Cette valeur n'est pas reconnue par cette version de Concentrator. Choisissez une autre valeur. | revised |
| `datetime_not_utc` | Dates and times must be in UTC and end with Z, for example 2026-11-06T16:44:03Z. | Les dates et heures doivent être en UTC et se terminer par Z, par exemple 2026-11-06T16:44:03Z. | revised |
| `storage_file_not_found` | The data file was not found. If it is on a removable or network drive, connect the drive. | Le fichier de données est introuvable. S'il est sur un disque amovible ou réseau, connectez ce disque. | revised |
| `storage_file_unreadable` | The data file cannot be read: another program is locking it or access is denied. Close the other program, then try again. | Le fichier de données ne peut pas être lu : un autre programme le verrouille ou l'accès est refusé. Fermez l'autre programme, puis réessayez. | revised |
| `storage_encoding_invalid` | The data file is not valid UTF-8 text. Save it again as UTF-8 in your text editor. | Le fichier de données n'est pas un texte UTF-8 valide. Enregistrez-le à nouveau en UTF-8 dans votre éditeur de texte. | revised |
| `storage_syntax_invalid` | The data file is damaged: syntax error at line {line}, column {column}. Correct it in a text editor, or restore a backup. | Le fichier de données est endommagé : erreur de syntaxe ligne {line}, colonne {column}. Corrigez-la dans un éditeur de texte ou restaurez une sauvegarde. | revised |
| `storage_field_missing` | A required value is missing. | Une valeur obligatoire est manquante. |  |
| `storage_field_unexpected` | The file contains a value that Concentrator does not know. | Le fichier contient une valeur que Concentrator ne connaît pas. |  |
| `storage_field_invalid_type` | A value has the wrong type. | Une valeur n'a pas le bon type. |  |
| `storage_field_invalid_value` | A value is invalid. | Une valeur n'est pas valide. |  |
| `storage_schema_version_unsupported` | This data file was written by a newer version of Concentrator. Update Concentrator to open it. | Ce fichier de données a été écrit par une version plus récente de Concentrator. Mettez Concentrator à jour pour l'ouvrir. |  |
| `storage_write_failed` | The data could not be written to disk. Check that the drive is connected and writable: Concentrator tries again automatically. | Les données n'ont pas pu être écrites sur le disque. Vérifiez que le disque est connecté et accessible en écriture : Concentrator réessaie automatiquement. | revised |
| `storage_verify_failed` | The data written to disk could not be verified, so the data file was not replaced. Concentrator tries again automatically. | Les données écrites sur le disque n'ont pas pu être vérifiées : le fichier de données n'a donc pas été remplacé. Concentrator réessaie automatiquement. | revised |
| `storage_replace_failed` | The data file could not be replaced: another program is probably using it (antivirus, backup or synchronization software). Close it, then try again. | Le fichier de données n'a pas pu être remplacé : un autre programme l'utilise probablement (antivirus, sauvegarde ou synchronisation). Fermez-le, puis réessayez. | revised |
| `storage_backup_failed` | The backup copy of the data file could not be made. Your data was saved. | La copie de sauvegarde du fichier de données n'a pas pu être faite. Vos données ont été enregistrées. |  |
| `storage_flush_timeout` | Saving did not finish in time. Your changes are still in memory: wait a moment, then try again. | L'enregistrement ne s'est pas terminé à temps. Vos modifications sont toujours en mémoire : patientez un instant, puis réessayez. | revised |
| `storage_file_already_exists` | A file already exists at this location. Open it instead of creating a new one. | Un fichier existe déjà à cet emplacement. Ouvrez-le au lieu d'en créer un nouveau. |  |
| `storage_directory_not_writable` | The folder or the file cannot be created at this location. Choose another folder. | Le dossier ou le fichier ne peut pas être créé à cet emplacement. Choisissez un autre dossier. | revised |
| `storage_disk_full` | The disk is full. Free some space, then try again. | Le disque est plein. Libérez de la place, puis réessayez. | revised |
| `storage_target_is_current_file` | This is already the current data file. Choose another file. | C'est déjà le fichier de données actuel. Choisissez un autre fichier. | revised |
| `storage_move_failed` | The data could not be moved: the new file does not contain the same data. The current file is still in use. | Les données n'ont pas pu être déplacées : le nouveau fichier ne contient pas les mêmes données. Le fichier actuel reste utilisé. |  |
| `storage_file_changed_externally` | The data file was changed outside Concentrator since it was last loaded or saved. Choose which version to keep. | Le fichier de données a été modifié en dehors de Concentrator depuis son dernier chargement ou enregistrement. Choisissez la version à garder. | revised |
| `config_file_not_found` | The configuration file concentrator.ini was not found. Put it back next to Concentrator.exe, or reinstall Concentrator. | Le fichier de configuration concentrator.ini est introuvable. Remettez-le à côté de Concentrator.exe ou réinstallez Concentrator. | revised |
| `config_syntax_invalid` | The configuration file concentrator.ini cannot be read. Correct it in a text editor, or reinstall Concentrator. | Le fichier de configuration concentrator.ini est illisible. Corrigez-le dans un éditeur de texte ou réinstallez Concentrator. | revised |
| `config_key_missing` | A required setting is missing from concentrator.ini. Add it back: the shipped file lists every setting. | Un paramètre obligatoire manque dans concentrator.ini. Ajoutez-le à nouveau : le fichier livré liste tous les paramètres. | revised |
| `config_value_invalid` | A setting of concentrator.ini has an invalid value. Correct it: the comment above each setting gives the allowed values. | Un paramètre de concentrator.ini a une valeur invalide. Corrigez-la : le commentaire au-dessus de chaque paramètre donne les valeurs permises. | revised |
| `config_key_unexpected` | concentrator.ini contains an unknown setting. Remove it or correct its spelling. | concentrator.ini contient un paramètre inconnu. Supprimez-le ou corrigez son orthographe. | revised |
| `catalog_file_not_found` | A language file is missing. Reinstall Concentrator. | Un fichier de langue est manquant. Réinstallez Concentrator. | revised |
| `catalog_syntax_invalid` | A language file is damaged. Reinstall Concentrator. | Un fichier de langue est endommagé. Réinstallez Concentrator. | revised |
| `catalog_key_missing` | A text is missing from a language file: the English text is shown instead. | Un texte manque dans un fichier de langue : le texte anglais est affiché à la place. | revised |
| `timer_duration_too_short` | The duration must be at least {min}. | La durée doit être d'au moins {min}. |  |
| `timer_duration_too_long` | The duration must not exceed {max}. | La durée ne doit pas dépasser {max}. |  |
| `timer_volume_out_of_range` | The volume must be between {min} and {max}. | Le volume doit être compris entre {min} et {max}. |  |
| `timer_loop_count_out_of_range` | The number of plays must be between {min} and {max}. | Le nombre de lectures doit être compris entre {min} et {max}. |  |
| `timer_auto_stop_out_of_range` | The automatic stop must be 0 (never) or between {min} and {max} seconds. | L'arrêt automatique doit valoir 0 (jamais) ou être compris entre {min} et {max} secondes. |  |
| `timer_transition_invalid` | This action is not possible in the current state of the timer. | Cette action n'est pas possible dans l'état actuel du minuteur. |  |
| `timer_sound_unset` | Please choose a sound. | Veuillez choisir un son. |  |
| `preset_duration_duplicate` | A favorite with the duration {duration} already exists. Choose another duration. | Un favori de durée {duration} existe déjà. Choisissez une autre durée. | revised |
| `preset_label_too_long` | The label must not exceed {max} characters. | Le libellé ne doit pas dépasser {max} caractères. |  |
| `preset_limit_reached` | You can keep at most {max} favorites. Delete one first. | Vous pouvez garder au plus {max} favoris. Supprimez-en d'abord un. | revised |
| `preset_label_character_invalid` | The label cannot contain these characters: {characters} | Le libellé ne peut pas contenir ces caractères : {characters} |  |
| `chime_hour_out_of_range` | The hour must be between {min} and {max}. | L'heure doit être comprise entre {min} et {max}. |  |
| `chime_hours_reversed` | The last chime cannot come before the first one. | Le dernier carillon ne peut pas précéder le premier. |  |
| `task_text_empty` | The first line of the task cannot be empty. | La première ligne de la tâche ne peut pas être vide. |  |
| `task_text_too_long` | The task text must not exceed {max} characters. | Le texte de la tâche ne doit pas dépasser {max} caractères. |  |
| `task_due_time_without_date` | A due time needs a due date: choose a date first. | Une heure d'échéance demande une date d'échéance : choisissez d'abord une date. | revised |
| `task_state_transition_invalid` | This change of state is not possible for this task. | Ce changement d'état n'est pas possible pour cette tâche. |  |
| `task_list_not_found` | The list of the task does not exist. Choose another list. | La liste de la tâche n'existe pas. Choisissez une autre liste. | revised |
| `list_name_empty` | The list name cannot be empty. | Le nom de la liste ne peut pas être vide. |  |
| `list_name_too_long` | The list name must not exceed {max} characters. | Le nom de la liste ne doit pas dépasser {max} caractères. |  |
| `list_name_duplicate` | A list with this name already exists. Choose another name. | Une liste porte déjà ce nom. Choisissez un autre nom. | revised |
| `list_description_too_long` | The description must not exceed {max} characters. | La description ne doit pas dépasser {max} caractères. |  |
| `list_not_empty` | The list still holds tasks. Move or delete them first. | La liste contient encore des tâches. Déplacez-les ou supprimez-les d'abord. | revised |
| `list_last_cannot_delete` | The last list cannot be deleted. Create another list first. | La dernière liste ne peut pas être supprimée. Créez d'abord une autre liste. | revised |
| `list_priority_unset` | Choose a priority. | Choisissez une priorité. |  |
| `recurrence_requires_due_date` | A repeating task needs a due date: choose one first. | Une tâche répétée demande une date d'échéance : choisissez-en d'abord une. | revised |
| `recurrence_interval_out_of_range` | The interval must be between {min} and {max}. | L'intervalle doit être compris entre {min} et {max}. |  |
| `recurrence_weekdays_empty` | Choose at least one day of the week. | Choisissez au moins un jour de la semaine. |  |
| `recurrence_end_date_before_due` | The end date cannot be before the due date. | La date de fin ne peut pas précéder la date d'échéance. |  |
| `recurrence_count_out_of_range` | The number of times must be between {min} and {max}. | Le nombre de fois doit être compris entre {min} et {max}. |  |
| `recurrence_frequency_unset` | Choose how often the task repeats. | Choisissez la fréquence de répétition. |  |
| `recurrence_end_kind_unset` | Choose when the repetition ends. | Choisissez quand la répétition s'arrête. |  |
| `recurrence_end_date_missing` | Choose the end date. | Choisissez la date de fin. |  |
| `focus_task_already_queued` | This task is already in the focus queue. | Cette tâche est déjà dans la file de concentration. |  |
| `focus_queue_full` | The focus queue is full ({max} tasks): remove a task first. | La file de concentration est pleine ({max} tâches) : retirez d'abord une tâche. |  |
| `focus_task_not_open` | Only open tasks can be added to the focus queue. Reopen the task first. | Seules les tâches ouvertes peuvent être ajoutées à la file de concentration. Rouvrez d'abord la tâche. | revised |
| `focus_task_missing` | A task of the focus queue no longer exists: it was left out of the queue. | Une tâche de la file de concentration n'existe plus : elle a été retirée de la file. |  |
| `link_open_failed` | Windows could not open this location. Check the path or the address, and that its drive is connected. | Windows n'a pas pu ouvrir cet emplacement. Vérifiez le chemin ou l'adresse, et que son disque est connecté. | revised |
| `audio_file_not_found` | The sound file was not found. Choose another sound. | Le fichier son est introuvable. Choisissez un autre son. | revised |
| `audio_format_unsupported` | This sound file cannot be played: its format is not supported. Choose an MP3 file. | Ce fichier son ne peut pas être lu : son format n'est pas pris en charge. Choisissez un fichier MP3. | revised |
| `audio_playback_failed` | The sound could not be played: Concentrator beeps instead. Choose another sound. | Le son n'a pas pu être lu : Concentrator émet un bip à la place. Choisissez un autre son. | revised |
| `audio_device_unavailable` | No audio output device is available: Concentrator beeps instead. Connect speakers or headphones. | Aucune sortie audio n'est disponible : Concentrator émet un bip à la place. Branchez des haut-parleurs ou un casque. | revised |
| `instance_lock_failed` | Concentrator cannot check whether it is already running, so two copies may run at once. Close any other Concentrator window. | Concentrator ne peut pas vérifier s'il est déjà lancé : deux exemplaires peuvent tourner en même temps. Fermez toute autre fenêtre de Concentrator. | revised |
| `instance_server_failed` | Concentrator cannot receive the requests of a second launch: launching it again will not bring this window to the front. Use the taskbar instead. | Concentrator ne peut pas recevoir les demandes d'un second lancement : le relancer ne ramènera pas cette fenêtre au premier plan. Utilisez plutôt la barre des tâches. | revised |
| `app_user_model_id_failed` | Windows refused the application identity; the taskbar may show Python instead of Concentrator. | Windows a refusé l'identité de l'application ; la barre des tâches peut afficher Python au lieu de Concentrator. |  |
