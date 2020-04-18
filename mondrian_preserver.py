import pandas as pd
from pyspark.sql.functions import PandasUDFType, lit, pandas_udf
from utils.utility import *


def anonymizer(df, partitions, feature_columns, sensitive_column, categorical, max_partitions=None):
    aggregations = {}

    for name in df.columns:
        if name not in categorical:
            df[name] = pd.to_numeric(df[name])

    for column in feature_columns:
        if column in categorical:
            aggregations[column] = agg_categorical_column
        else:
            aggregations[column] = agg_numerical_column
    rows = []

    for i, partition in enumerate(partitions):
        if i % 100 == 1:
            print("Finished {} partitions.".format(i))
        if max_partitions is not None and i > max_partitions:
            break
        grouped_columns = df.loc[partition].assign(
            _common88column_=1).groupby('_common88column_').agg(aggregations, squeeze=False)
        sensitive_counts = df.loc[partition].groupby(
            sensitive_column).agg({sensitive_column: 'count'})
        values = grouped_columns.iloc[0].to_dict()
        for sensitive_value, count in sensitive_counts[sensitive_column].items():
            if count == 0:
                continue
            values.update({
                sensitive_column: sensitive_value,
                'count': count,

            })
            rows.append(values.copy())
    dfn = pd.DataFrame(rows)
    pdfn = dfn.sort_values(feature_columns+[sensitive_column])
    return pdfn


def k_anonymizer(df, k, feature_columns, sensitive_column, categorical):

    full_spans = get_spans(df, categorical, df.index)

    partitions = partition_dataset(
        df, k, None,  categorical, feature_columns, sensitive_column, full_spans)

    return anonymizer(df, partitions, feature_columns, sensitive_column, categorical)


def l_diversity(df, k, l, feature_columns, sensitive_column, categorical):

    full_spans = get_spans(df, categorical, df.index)

    partitions = partition_dataset(
        df, k, l,  categorical, feature_columns, sensitive_column, full_spans)

    return anonymizer(df, partitions, feature_columns, sensitive_column, categorical)


class Preserver:

    @staticmethod
    def k_anonymize(pdf, k, feature_columns, sensitive_column, categorical, schema):

        @pandas_udf(schema, PandasUDFType.GROUPED_MAP)
        def anonymize(pdf):
            df = k_anonymizer(pdf, k, feature_columns,
                              sensitive_column, categorical)
            return df

        # TODO decide wether to keep this or not
        new_df = pdf.withColumn("_common888column_", lit(0))
        return new_df.groupby('_common888column_').apply(anonymize)

        # return pdf.groupby('common').apply(anonymize)

    @staticmethod
    def l_diversity(pdf, k, l, feature_columns, sensitive_column, categorical, schema):

        @pandas_udf(schema, PandasUDFType.GROUPED_MAP)
        def anonymize(pdf):
            df = l_diversity(pdf, k, feature_columns,
                             sensitive_column, categorical)

        # TODO decide wether to keep this or not
        new_df = pdf.withColumn("_common888column_", lit(0))
        return new_df.groupby('_common888column_').apply(anonymize)

        # return pdf.groupby('common').apply(anonymize)
