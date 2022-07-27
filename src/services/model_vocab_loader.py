#!/usr/bin/env python3 -u
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Translate raw text with a trained model. Batches data on-the-fly.
"""

INDIC_NLP_LIB_HOME = "src/tools/indic_nlp_library"
INDIC_NLP_RESOURCES = "src/tools/indic_nlp_resources"
import sys

sys.path.append(r"{}".format(INDIC_NLP_LIB_HOME))
from indicnlp import common

common.set_resources_path(INDIC_NLP_RESOURCES)
from indicnlp import loader
loader.load()

import ast
from collections import namedtuple
from pprint import pformat, pprint
import numpy as np

import torch
from fairseq import checkpoint_utils, options, tasks, utils
from fairseq.dataclass.utils import convert_namespace_to_omegaconf
from fairseq.token_generation_constraints import pack_constraints, unpack_constraints
from fairseq_cli.generate import get_symbols_to_strip_from_output
from indicnlp.transliterate import unicode_transliterate
from indicnlp.tokenize import indic_detokenize
from sacremoses import MosesDetokenizer

import codecs

from tools.apply_bpe import BPE, read_vocabulary


Batch = namedtuple("Batch", "ids src_tokens src_lengths constraints")
Translation = namedtuple("Translation", "src_str hypos pos_scores alignments")


def make_batches(
    lines, cfg, task, max_positions, encode_fn, constrainted_decoding=False
):
    def encode_fn_target(x):
        return encode_fn(x)

    if constrainted_decoding:
        # Strip (tab-delimited) contraints, if present, from input lines,
        # store them in batch_constraints
        batch_constraints = [list() for _ in lines]
        for i, line in enumerate(lines):
            if "\t" in line:
                lines[i], *batch_constraints[i] = line.split("\t")

        # Convert each List[str] to List[Tensor]
        for i, constraint_list in enumerate(batch_constraints):
            batch_constraints[i] = [
                task.target_dictionary.encode_line(
                    encode_fn_target(constraint),
                    append_eos=False,
                    add_if_not_exist=False,
                )
                for constraint in constraint_list
            ]

    if constrainted_decoding:
        constraints_tensor = pack_constraints(batch_constraints)
    else:
        constraints_tensor = None

    tokens, lengths = task.get_interactive_tokens_and_lengths(lines, encode_fn)

    itr = task.get_batch_iterator(
        dataset=task.build_dataset_for_inference(
            tokens, lengths, constraints=constraints_tensor
        ),
        max_tokens=cfg.dataset.max_tokens,
        max_sentences=cfg.dataset.batch_size,
        max_positions=max_positions,
        ignore_invalid_inputs=cfg.dataset.skip_invalid_size_inputs_valid_test,
    ).next_epoch_itr(shuffle=False)
    for batch in itr:
        ids = batch["id"]
        src_tokens = batch["net_input"]["src_tokens"]
        src_lengths = batch["net_input"]["src_lengths"]
        constraints = batch.get("constraints", None)

        yield Batch(
            ids=ids,
            src_tokens=src_tokens,
            src_lengths=src_lengths,
            constraints=constraints,
        )
def get_hypo_word(in_map, hypo_word, lang, common_lang='hi' ):
    final_word = ''
    if in_map >= len(hypo_word):
        final_word =  ''
    elif in_map < 0:
        final_word =  ''
    elif hypo_word[in_map].endswith('@@'):
        final_word = final_word + hypo_word[in_map][:-2]
        i = 1
        while in_map + i < len(hypo_word):
            if hypo_word[in_map + i].endswith('@@'):
                final_word = final_word + hypo_word[in_map+i][:-2]
            else:
                final_word = final_word + hypo_word[in_map +i]
                break
            i += 1
    else:
        final_word = final_word + hypo_word[in_map]
    i = 1
    while in_map -i >= 0:
        if hypo_word[in_map-i].endswith('@@'):
            final_word = hypo_word[in_map-i][:-2] + final_word
        else:
            break
        i += 1
    # if in_map < len(hypo_word):
    #     print(f"\n{in_map}-{hypo_word[in_map]}-{final_word}\n")
    # else:
    #     print(f"\n{in_map}-<eos>-{final_word}\n")
    if lang == "en":
        en_detok = MosesDetokenizer(lang="en")
        final_word = en_detok.detokenize(final_word.strip().split(" "))
    else:
        xliterator = unicode_transliterate.UnicodeIndicTransliterator()
        final_word = indic_detokenize.trivial_detokenize(
            xliterator.transliterate(final_word.strip(), common_lang, lang), lang
        )
    return final_word

class Translator:
    def __init__(
        self, data_dir, checkpoint_path, batch_size=25, constrained_decoding=False
    ):

        self.constrained_decoding = constrained_decoding
        self.parser = options.get_generation_parser(interactive=True)
        # buffer_size is currently not used but we just initialize it to batch
        # size + 1 to avoid any assertion errors.
        if self.constrained_decoding:
            self.parser.set_defaults(
                path=checkpoint_path,
                remove_bpe="subword_nmt",
                num_wokers=-1,
                constraints="ordered",
                batch_size=batch_size,
                buffer_size=batch_size + 1,
                # print_alignment = "soft",
            )
        else:
            self.parser.set_defaults(
                path=checkpoint_path,
                remove_bpe="subword_nmt",
                num_wokers=-1,
                batch_size=batch_size,
                buffer_size=batch_size + 1,
                print_alignment = "soft",
            )
        args = options.parse_args_and_arch(self.parser, input_args=[data_dir])
        # we are explictly setting src_lang and tgt_lang here
        # generally the data_dir we pass contains {split}-{src_lang}-{tgt_lang}.*.idx files from
        # which fairseq infers the src and tgt langs(if these are not passed). In deployment we dont
        # use any idx files and only store the SRC and TGT dictionaries.
        args.source_lang = "SRC"
        args.target_lang = "TGT"
        
        args.skip_invalid_size_inputs_valid_test = False

        # we have custom architechtures in this folder and we will let fairseq
        # import this
        args.user_dir = "src/model_configs"
        self.cfg = convert_namespace_to_omegaconf(args)

        utils.import_user_module(self.cfg.common)

        if self.cfg.interactive.buffer_size < 1:
            self.cfg.interactive.buffer_size = 1
        if self.cfg.dataset.max_tokens is None and self.cfg.dataset.batch_size is None:
            self.cfg.dataset.batch_size = 1

        assert (
            not self.cfg.generation.sampling
            or self.cfg.generation.nbest == self.cfg.generation.beam
        ), "--sampling requires --nbest to be equal to --beam"
        assert (
            not self.cfg.dataset.batch_size
            or self.cfg.dataset.batch_size <= self.cfg.interactive.buffer_size
        ), "--batch-size cannot be larger than --buffer-size"

        # Fix seed for stochastic decoding
        # if self.cfg.common.seed is not None and not self.cfg.generation.no_seed_provided:
        #     np.random.seed(self.cfg.common.seed)
        #     utils.set_torch_seed(self.cfg.common.seed)

        # if not self.constrained_decoding:
        #     self.use_cuda = torch.cuda.is_available() and not self.cfg.common.cpu
        # else:
        #     self.use_cuda = False    
            
        self.use_cuda = torch.cuda.is_available() and not self.cfg.common.cpu

        # Setup task, e.g., translation
        self.task = tasks.setup_task(self.cfg.task)

        # Load ensemble
        overrides = ast.literal_eval(self.cfg.common_eval.model_overrides)
        self.models, self._model_args = checkpoint_utils.load_model_ensemble(
            utils.split_paths(self.cfg.common_eval.path),
            arg_overrides=overrides,
            task=self.task,
            suffix=self.cfg.checkpoint.checkpoint_suffix,
            strict=(self.cfg.checkpoint.checkpoint_shard_count == 1),
            num_shards=self.cfg.checkpoint.checkpoint_shard_count,
        )

        # Set dictionaries
        self.src_dict = self.task.source_dictionary
        self.tgt_dict = self.task.target_dictionary

        # Optimize ensemble for generation
        for model in self.models:
            if model is None:
                continue
            if self.cfg.common.fp16:
                model.half()
            if (
                self.use_cuda
                and not self.cfg.distributed_training.pipeline_model_parallel
            ):
                model.cuda()
            model.prepare_for_inference_(self.cfg)

        # Initialize generator
        self.generator = self.task.build_generator(self.models, self.cfg.generation)

        # Handle tokenization and BPE
        self.tokenizer = self.task.build_tokenizer(self.cfg.tokenizer)
        self.bpe = self.task.build_bpe(self.cfg.bpe)

        # Load alignment dictionary for unknown word replacement
        # (None if no unknown word replacement, empty if no path to align dictionary)
        self.align_dict = utils.load_align_dict(self.cfg.generation.replace_unk)

        self.max_positions = utils.resolve_max_positions(
            self.task.max_positions(), *[model.max_positions() for model in self.models]
        )

    def encode_fn(self, x):
        if self.tokenizer is not None:
            x = self.tokenizer.encode(x)
        if self.bpe is not None:
            x = self.bpe.encode(x)
        return x

    def decode_fn(self, x):
        if self.bpe is not None:
            x = self.bpe.decode(x)
        if self.tokenizer is not None:
            x = self.tokenizer.decode(x)
        return x

    def translate(self, inputs, constraints=None):
        if self.constrained_decoding and constraints is None:
            raise ValueError("Constraints cant be None in constrained decoding mode")
        if not self.constrained_decoding and constraints is not None:
            raise ValueError("Cannot pass constraints during normal translation")
        if constraints:
            constrained_decoding = True
            modified_inputs = []
            for _input, constraint in zip(inputs, constraints):
                modified_inputs.append(_input + f"\t{constraint}")
            inputs = modified_inputs
        else:
            constrained_decoding = False

        start_id = 0
        results = []
        final_translations = []
        for batch in make_batches(
            inputs,
            self.cfg,
            self.task,
            self.max_positions,
            self.encode_fn,
            constrained_decoding,
        ):
            bsz = batch.src_tokens.size(0)
            src_tokens = batch.src_tokens
            src_lengths = batch.src_lengths
            constraints = batch.constraints
            if self.use_cuda:    
                src_tokens = src_tokens.cuda()
                src_lengths = src_lengths.cuda()
                if constraints is not None:
                    constraints = constraints.cuda()
                        

            sample = {
                "net_input": {
                    "src_tokens": src_tokens,
                    "src_lengths": src_lengths,
                },
            }               
                
            translations = self.task.inference_step(
                self.generator, self.models, sample, constraints=constraints
            )

            list_constraints = [[] for _ in range(bsz)]
            if constrained_decoding:
                list_constraints = [unpack_constraints(c) for c in constraints]
            for i, (id, hypos) in enumerate(zip(batch.ids.tolist(), translations)):
                src_tokens_i = utils.strip_pad(src_tokens[i], self.tgt_dict.pad())
                constraints = list_constraints[i]
                results.append(
                    (
                        start_id + id,
                        src_tokens_i,
                        hypos,
                        {
                            "constraints": constraints,
                        },
                    )
                )

        # sort output to match input order
        for id_, src_tokens, hypos, _ in sorted(results, key=lambda x: x[0]):
            src_str = ""
            if self.src_dict is not None:
                src_str = self.src_dict.string(
                    src_tokens, self.cfg.common_eval.post_process
                )

            # Process top predictions
            for hypo in hypos[: min(len(hypos), self.cfg.generation.nbest)]:
                hypo_tokens, hypo_str, alignment = utils.post_process_prediction(
                    hypo_tokens=hypo["tokens"].int().cpu(),
                    src_str=src_str,
                    alignment=hypo["alignment"],
                    align_dict=self.align_dict,
                    tgt_dict=self.tgt_dict,
                    remove_bpe="subword_nmt",
                    extra_symbols_to_ignore=get_symbols_to_strip_from_output(
                        self.generator
                    ),
                )
                detok_hypo_str = self.decode_fn(hypo_str)
                final_translations.append(detok_hypo_str)
        return {'translations':final_translations}


    def translate_with_tokenmap(self, inputs, constraints=None):
        if self.constrained_decoding and constraints is None:
            raise ValueError("Constraints cant be None in constrained decoding mode")
        if not self.constrained_decoding and constraints is not None:
            raise ValueError("Cannot pass constraints during normal translation")
        if constraints:
            constrained_decoding = True
            modified_inputs = []
            for _input, constraint in zip(inputs, constraints):
                modified_inputs.append(_input + f"\t{constraint}")
            inputs = modified_inputs
        else:
            constrained_decoding = False

        start_id = 0
        results = []
        final_translations = []
        token_map_list = []
        for batch in make_batches(
            inputs,
            self.cfg,
            self.task,
            self.max_positions,
            self.encode_fn,
            constrained_decoding,
        ):
            bsz = batch.src_tokens.size(0)
            src_tokens = batch.src_tokens
            src_lengths = batch.src_lengths
            constraints = batch.constraints
            if self.use_cuda:    
                src_tokens = src_tokens.cuda()
                src_lengths = src_lengths.cuda()
                if constraints is not None:
                    constraints = constraints.cuda()
                        

            sample = {
                "net_input": {
                    "src_tokens": src_tokens,
                    "src_lengths": src_lengths,
                },
            }               
                
            translations = self.task.inference_step(
                self.generator, self.models, sample, constraints=constraints
            )

            list_constraints = [[] for _ in range(bsz)]
            if constrained_decoding:
                list_constraints = [unpack_constraints(c) for c in constraints]
            for i, (id, hypos) in enumerate(zip(batch.ids.tolist(), translations)):
                src_tokens_i = utils.strip_pad(src_tokens[i], self.tgt_dict.pad())
                constraints = list_constraints[i]
                results.append(
                    (
                        start_id + id,
                        src_tokens_i,
                        hypos,
                        {
                            "constraints": constraints,
                        },
                    )
                )

        # sort output to match input order
        for id_, src_tokens, hypos, _ in sorted(results, key=lambda x: x[0]):
            src_str = ""
            if self.src_dict is not None:
                src_str = self.src_dict.string(
                    src_tokens, self.cfg.common_eval.post_process
                )

            # Process top predictions
            for hypo in hypos[: min(len(hypos), self.cfg.generation.nbest)]:
                hypo_tokens, hypo_str, alignment = utils.post_process_prediction(
                    hypo_tokens=hypo["tokens"].int().cpu(),
                    src_str=src_str,
                    alignment=hypo["alignment"],
                    align_dict=self.align_dict,
                    tgt_dict=self.tgt_dict,
                    remove_bpe="subword_nmt",
                    extra_symbols_to_ignore=get_symbols_to_strip_from_output(
                        self.generator
                    ),
                )
                detok_hypo_str = self.decode_fn(hypo_str)
                final_translations.append(detok_hypo_str)
                hypo_tokens, hypo_str, alignment = utils.post_process_prediction(
                    hypo_tokens=hypo["tokens"].int().cpu(),
                    src_str=src_str,
                    alignment=hypo["alignment"],
                    align_dict=self.align_dict,
                    tgt_dict=self.tgt_dict,
                    remove_bpe=self.cfg.common_eval.post_process,
                    extra_symbols_to_ignore=get_symbols_to_strip_from_output(
                        self.generator
                    ), 
                )
                atten_src_token = np.array(alignment).T
                src_token_map = np.argmax(atten_src_token, axis=1).tolist()
                # print(f"Source token map is {src_token_map} with length {len(src_token_map)}")
                # print("source string", src_str, len(src_str.split()))
                # print("target_str", hypo_str, len(hypo_str.split()))
                src_word = src_str.split()
                hypo_word = hypo_str.split()
                target_language_code = src_word[1].split('__')[-2]
                # Exluding last token as its end of sentence tag
                skip = False
                assemble_word = ''
                token_map = []
                for i,in_map in enumerate(src_token_map[:-1]):
                    if skip and src_word[i].endswith('@@'): 
                        assemble_word = assemble_word + src_word[i][:-2]
                        continue
                    elif assemble_word:
                        assemble_word = assemble_word + src_word[i]
                        # print(f"{assemble_word}-{assemble_word_tgt}")
                        token_map.append((assemble_word, assemble_word_tgt))
                        assemble_word = ''
                        skip = False
                        continue
                    if src_word[i].endswith("@@"):
                        skip = True
                        assemble_word = assemble_word + src_word[i][:-2]
                        assemble_word_tgt = get_hypo_word(in_map, hypo_word, target_language_code)
                        continue
                    # print(f"{src_word[i]}-{get_hypo_word(in_map, hypo_word, target_language_code)}")
                    token_map.append((src_word[i],get_hypo_word(in_map, hypo_word, target_language_code)))
                token_map_list.append(token_map[2:])
        if not len(final_translations) == len(token_map_list):
            raise ValueError('no of sentences translated dosent match no of token map generated. Check Code base in Translator Class') 
        return {'translations': final_translations, 'token_maps': token_map_list}

def load_vocab(vocab_path, bpe_codes_path):
    vocabulary = read_vocabulary(codecs.open(vocab_path, encoding="utf-8"), 5)
    bpe = BPE(
        codecs.open(bpe_codes_path, encoding="utf-8"),
        -1,
        "@@",
        vocabulary,
        None,
    )
    return bpe
