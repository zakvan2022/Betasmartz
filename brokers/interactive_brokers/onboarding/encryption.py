import gnupg
import io


def encrypt(path_to_files,
            zipped,
            keys,
            encrypted,
            our_secret_uids,
            their_public_uids,
            zip_file):
    '''
    writes file (encrypted with their_public_uids public key, and signed with
    our_secret_uids private key)
    '''
    gpg = gnupg.GPG(gnupghome=path_to_files + keys[:-1], verbose=True)
    key_fingerprint = get_key_fingerprint(gpg, our_secret_uids, False)

    with io.open(path_to_files + zipped + zip_file, 'rb') as zip_file_stream:
        output_file = path_to_files + encrypted + zip_file + '.gpg'
        encrypted_msg = gpg.encrypt_file(zip_file_stream,
                                         their_public_uids,
                                         sign = key_fingerprint,
                                         always_trust=True,
                                         output=output_file)
    zip_file_stream.close()


def get_key_fingerprint(gpg, uids, private):
    '''
    returns fingerprint of key (public or private) with given uids
    '''
    keys = list_keys(gpg, private)

    for key in keys:
        if key['uids'][0] == uids:
            return key['fingerprint']

    raise Exception('key not found for uids='+ str(uids) + ' private=' + str(private))


def list_keys(gpg, private):
    '''
    returns list of keys on given key ring
    '''
    keys = gpg.list_keys(private)
    return keys
