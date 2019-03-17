from argparse import ArgumentParser
import os


def get_args():
    parser = ArgumentParser(description="HAN")
    parser.add_argument('--word_num_hidden', type=int, default=50)
    parser.add_argument('--sentence_num_hidden', type=int, default=50)

    parser.add_argument('--single_label', action='store_true')
    parser.add_argument('--mode', type=str, default='static', choices=['rand', 'static', 'non-static'])
    parser.add_argument('--dataset', type=str, default='SST-1', choices=['SST-1', 'SST-2', 'Reuters', 'AAPD', 'IMDB', 'Yelp2014'])
    parser.add_argument('--resume_snapshot', type=str, default=None)
    parser.add_argument('--save_path', type=str, default='han/saves')
    parser.add_argument('--output_channel', type=int, default=100)
    parser.add_argument('--words_dim', type=int, default=300)
    parser.add_argument('--embed_dim', type=int, default=300)
    parser.add_argument('--dropout', type=float, default=0.5)
    parser.add_argument('--epoch_decay', type=int, default=15)
    parser.add_argument('--word-vectors-dir', default=os.path.join(os.pardir, 'Castor-data', 'embeddings', 'word2vec'))
    parser.add_argument('--word-vectors-file', default='GoogleNews-vectors-negative300.txt')
    parser.add_argument('--trained_model', type=str, default="")
    parser.add_argument('--weight_decay', type=float, default=0)
    parser.add_argument('--onnx', action='store_true', default=False, help='Export model in ONNX format')
    parser.add_argument('--onnx_batch_size', type=int, default=1024, help='Batch size for ONNX export')
    parser.add_argument('--onnx_sent_len', type=int, default=32, help='Sentence length for ONNX export')

    args = parser.parse_args()
    return args
